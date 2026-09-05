"""
Snowpark Python Job: Feature Engineering for dim_produto

This job demonstrates how to use Snowpark Python to:
1. Read from Silver layer (stg_dim_produto)
2. Apply feature engineering (categorical encoding, price buckets, etc.)
3. Write enriched features to Gold layer (gld_dim_produto_features)

Usage:
    python src/snowpark/jobs/feature_engineering_dim_produto.py \
        --account <account> \
        --user <user> \
        --password <password> \
        --warehouse <warehouse> \
        --database <database> \
        --schema <schema>

Or set environment variables:
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
    SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA
"""

import os
import argparse
from typing import Optional

from snowflake.snowpark import Session
from snowflake.snowpark.functions import (
    col, when, lit, round as sp_round,
    trim,
    min as sp_min, max as sp_max, avg as sp_avg
)
from snowflake.snowpark.types import (
    IntegerType
)


def create_session(
    account: str,
    user: str,
    password: str,
    warehouse: str,
    database: str,
    schema: str,
    role: Optional[str] = None,
) -> Session:
    """Create Snowpark session with connection parameters."""
    connection_params = {
        "account": account,
        "user": user,
        "password": password,
        "warehouse": warehouse,
        "database": database,
        "schema": schema,
    }
    if role:
        connection_params["role"] = role
    
    session = Session.builder.configs(connection_params).create()
    session.sql_simplifier_enabled = True
    return session


def read_silver_produto(session: Session, schema: str = "SILVER"):
    """Read dim_produto from Silver layer."""
    return session.table(f"{schema}.STG_DIM_PRODUTO")


def engineer_features(df):
    """Apply feature engineering to produto data."""
    
    # 1. Price bucketing
    df = df.with_column(
        "price_bucket",
        when(col("preco_unitario") < 50, "LOW")
        .when(col("preco_unitario") < 200, "MEDIUM")
        .when(col("preco_unitario") < 500, "HIGH")
        .otherwise("PREMIUM")
    )
    
    # 2. Price percentile rank (using window function would be better in production)
    # For demo, using simple bucketing based on min/max
    stats = df.agg(
        sp_min("preco_unitario").alias("min_price"),
        sp_max("preco_unitario").alias("max_price"),
        sp_avg("preco_unitario").alias("avg_price"),
    ).collect()[0]
    
    min_price = stats["MIN_PRICE"]
    max_price = stats["MAX_PRICE"]
    avg_price = stats["AVG_PRICE"]
    price_range = max_price - min_price
    
    # Normalized price (0-1)
    df = df.with_column(
        "price_normalized",
        sp_round((col("preco_unitario") - lit(min_price)) / lit(price_range), 4)
    )
    
    # 3. Category encoding - one-hot style for categoria
    categories = df.select("categoria").distinct().collect()
    for cat_row in categories:
        cat = cat_row["CATEGORIA"]
        if cat:
            col_name = f"is_{cat.lower().replace(' ', '_').replace('-', '_')}"
            df = df.with_column(
                col_name,
                when(col("categoria") == lit(cat), lit(1)).otherwise(lit(0))
            )
    
    # 4. Brand/manufacturer flag
    df = df.with_column(
        "has_fabricante",
        when(col("fabricante").is_not_null() & (trim(col("fabricante")) != ""), lit(1)).otherwise(lit(0))
    )
    
    # 5. Product name length (proxy for complexity)
    df = df.with_column(
        "nome_length",
        col("nome_produto").length()
    )
    
    # 6. Price vs average flag
    df = df.with_column(
        "above_avg_price",
        when(col("preco_unitario") > lit(avg_price), lit(1)).otherwise(lit(0))
    )
    
    # 7. SKU pattern analysis (extract numeric suffix if exists)
    df = df.with_column(
        "sku_numeric_suffix",
        when(
            col("sku_produto").rlike(".*\\d+$"),
            col("sku_produto").regexp_extract("(\\d+)$", 1).cast(IntegerType())
        ).otherwise(lit(None))
    )
    
    return df


def write_gold_features(session: Session, df, schema: str = "GOLD", table: str = "GLD_DIM_PRODUTO_FEATURES"):
    """Write enriched features to Gold layer."""
    # Create table if not exists
    session.sql(f"""
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            sku_produto STRING PRIMARY KEY,
            nome_produto STRING,
            categoria STRING,
            fabricante STRING,
            preco_unitario DOUBLE,
            price_bucket STRING,
            price_normalized DOUBLE,
            above_avg_price INTEGER,
            has_fabricante INTEGER,
            nome_length INTEGER,
            sku_numeric_suffix INTEGER
        )
    """).collect()
    
    # For demo: overwrite (in production use merge)
    df.write.mode("overwrite").save_as_table(f"{schema}.{table}")
    print(f"✓ Written {df.count()} rows to {schema}.{table}")


def main():
    parser = argparse.ArgumentParser(description="Snowpark Feature Engineering for dim_produto")
    parser.add_argument("--account", default=os.getenv("SNOWFLAKE_ACCOUNT"))
    parser.add_argument("--user", default=os.getenv("SNOWFLAKE_USER"))
    parser.add_argument("--password", default=os.getenv("SNOWFLAKE_PASSWORD"))
    parser.add_argument("--warehouse", default=os.getenv("SNOWFLAKE_WAREHOUSE"))
    parser.add_argument("--database", default=os.getenv("SNOWFLAKE_DATABASE"))
    parser.add_argument("--schema", default=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"))
    parser.add_argument("--role", default=os.getenv("SNOWFLAKE_ROLE"))
    parser.add_argument("--source-schema", default="SILVER", help="Source schema (Silver layer)")
    parser.add_argument("--target-schema", default="GOLD", help="Target schema (Gold layer)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    
    args = parser.parse_args()
    
    # Validate required params
    required = ["account", "user", "password", "warehouse", "database"]
    missing = [p for p in required if not getattr(args, p)]
    if missing:
        parser.error(f"Missing required arguments: {missing}. Set env vars or pass via CLI.")
    
    print(f"Connecting to Snowflake: {args.account}/{args.database}.{args.schema}")
    
    if args.dry_run:
        print("DRY RUN - would execute:")
        print(f"  Source: {args.source_schema}.STG_DIM_PRODUTO")
        print(f"  Target: {args.target_schema}.GLD_DIM_PRODUTO_FEATURES")
        return
    
    session = create_session(
        account=args.account,
        user=args.user,
        password=args.password,
        warehouse=args.warehouse,
        database=args.database,
        schema=args.schema,
        role=args.role,
    )
    
    try:
        print("Reading Silver layer...")
        df_silver = read_silver_produto(session, args.source_schema)
        print(f"  Rows: {df_silver.count()}")
        df_silver.show(5)
        
        print("Engineering features...")
        df_features = engineer_features(df_silver)
        print(f"  Columns: {df_features.columns}")
        df_features.show(5)
        
        print("Writing to Gold layer...")
        write_gold_features(session, df_features, args.target_schema)
        
        print("✓ Feature engineering completed successfully!")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()