"""
Snowpark UDFs for reusable feature engineering.

These UDFs can be registered in Snowflake and used in SQL queries.
"""

from snowflake.snowpark import Session
from snowflake.snowpark.functions import udf
from snowflake.snowpark.types import StringType, DoubleType, IntegerType
import re


from typing import Optional

# ─── Price bucket UDF ───
def price_bucket_udf(price: Optional[float]) -> str:
    """Categorize price into buckets."""
    if price is None:
        return "UNKNOWN"
    if price < 50:
        return "LOW"
    elif price < 200:
        return "MEDIUM"
    elif price < 500:
        return "HIGH"
    return "PREMIUM"


# ─── Price normalization UDF ───
def normalize_price_udf(price: float, min_price: float, max_price: float) -> float:
    """Normalize price to 0-1 range."""
    if price is None or min_price is None or max_price is None:
        return None
    if max_price == min_price:
        return 0.5
    return round((price - min_price) / (max_price - min_price), 4)


# ─── Category one-hot encoding UDF ───
def category_flag_udf(category: str, target_category: str) -> int:
    """Return 1 if category matches target, else 0."""
    if category is None or target_category is None:
        return 0
    return 1 if category.strip().lower() == target_category.strip().lower() else 0


# ─── SKU numeric suffix extractor ───
def sku_numeric_suffix_udf(sku: str) -> int | None:
    """Extract numeric suffix from SKU if present."""
    if not sku:
        return None
    match = re.search(r"(\d+)$", sku)
    return int(match.group(1)) if match else None


# ─── Product name complexity score ───
def name_complexity_udf(name: str) -> int:
    """Return length of product name as complexity proxy."""
    if not name:
        return 0
    return len(name.strip())


def register_udfs(session: Session) -> dict:
    """Register all UDFs in Snowflake session and return them."""
    
    udfs = {
        "price_bucket": udf(
            price_bucket_udf,
            return_type=StringType(),
            input_types=[DoubleType()],
            name="PRICE_BUCKET",
            replace=True,
            is_permanent=False,  # Set True to persist across sessions
        ),
        "normalize_price": udf(
            normalize_price_udf,
            return_type=DoubleType(),
            input_types=[DoubleType(), DoubleType(), DoubleType()],
            name="NORMALIZE_PRICE",
            replace=True,
        ),
        "category_flag": udf(
            category_flag_udf,
            return_type=IntegerType(),
            input_types=[StringType(), StringType()],
            name="CATEGORY_FLAG",
            replace=True,
        ),
        "sku_numeric_suffix": udf(
            sku_numeric_suffix_udf,
            return_type=IntegerType(),
            input_types=[StringType()],
            name="SKU_NUMERIC_SUFFIX",
            replace=True,
        ),
        "name_complexity": udf(
            name_complexity_udf,
            return_type=IntegerType(),
            input_types=[StringType()],
            name="NAME_COMPLEXITY",
            replace=True,
        ),
    }
    
    return udfs


# Example usage in SQL:
"""
-- After registering UDFs, use in SQL:
SELECT 
    sku_produto,
    nome_produto,
    preco_unitario,
    PRICE_BUCKET(preco_unitario) as price_bucket,
    NORMALIZE_PRICE(preco_unitario, 10.0, 1000.0) as price_norm,
    CATEGORY_FLAG(categoria, 'ELETRONICOS') as is_electronics,
    SKU_NUMERIC_SUFFIX(sku_produto) as sku_suffix,
    NAME_COMPLEXITY(nome_produto) as name_len
FROM SILVER.STG_DIM_PRODUTO;
"""


if __name__ == "__main__":
    # Test UDFs locally (without Snowflake)
    test_prices = [25.0, 150.0, 350.0, 750.0, None]
    for p in test_prices:
        print(f"price={p} -> bucket={price_bucket_udf(p)}")
    
    test_skus = ["PROD-001", "ABC", "ITEM-12345", ""]
    for s in test_skus:
        print(f"sku={s!r} -> suffix={sku_numeric_suffix_udf(s)}")