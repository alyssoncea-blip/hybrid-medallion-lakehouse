"""generate_bronze.py

Generates synthetic Parquet files for the Bronze layer, mimicking a batch
extraction from SAP SD/Oracle OMS (pedidos) and Salesforce CRM (clientes).

This is a *fixture generator* — it creates realistic data shapes for local dbt
development. Production ingestion happens via Snowpipe from real S3.

Usage:
    python scripts/generate_bronze.py [--rows-pedidos N] [--rows-clientes M]

Default output: data/bronze/pedidos_vendas/*.parquet
                data/bronze/clientes_cadastro/*.parquet
"""

from __future__ import annotations

import argparse
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
BRONZE_DIR = ROOT / "data" / "bronze"

STATUS_CHOICES = ["ABERTO", "PAGO", "FATURADO", "CANCELADO", "DEVOLVIDO"]
CANAL_CHOICES = ["E-COMMERCE", "LOJA", "WHATSAPP", "MARKETPLACE"]
VENDEDOR_CHOICES = [f"V{str(i).zfill(4)}" for i in range(1, 21)] + ["UNASSIGNED"]


def random_cpf(rng: random.Random) -> str:
    """Generate a syntactically valid (but not real) CPF."""
    nums = [rng.randint(0, 9) for _ in range(9)]
    # First check digit
    s = sum(x * (10 - i) for i, x in enumerate(nums))
    d1 = (s * 10 % 11) % 10
    nums.append(d1)
    # Second check digit
    s = sum(x * (11 - i) for i, x in enumerate(nums))
    d2 = (s * 10 % 11) % 10
    nums.append(d2)
    return "".join(map(str, nums))


def generate_pedidos(rows: int, start_date: date, end_date: date, seed: int = 42) -> pa.Table:
    rng = random.Random(seed)
    delta_days = (end_date - start_date).days
    data = {
        "pedido_id": [f"P{str(i).zfill(8)}" for i in range(1, rows + 1)],
        "cliente_id": [f"C{str(rng.randint(1, max(1, rows // 4))).zfill(6)}" for _ in range(rows)],
        "data_pedido": [
            start_date + timedelta(days=rng.randint(0, delta_days))
            for _ in range(rows)
        ],
        "valor_total": [round(rng.uniform(50.0, 5000.0), 2) for _ in range(rows)],
        "status": [rng.choice(STATUS_CHOICES) for _ in range(rows)],
        "vendedor_id": [rng.choice(VENDEDOR_CHOICES) for _ in range(rows)],
        "canal_venda": [rng.choice(CANAL_CHOICES) for _ in range(rows)],
    }
    return pa.table(data)


def generate_clientes(rows: int, seed: int = 42) -> pa.Table:
    rng = random.Random(seed)
    data = {
        "cliente_id": [f"C{str(i).zfill(6)}" for i in range(1, rows + 1)],
        "nome": [f"Cliente {i}" for i in range(1, rows + 1)],
        "cpf": [random_cpf(rng) for _ in range(rows)],
        "email": [f"cliente{i}@example.com" for i in range(1, rows + 1)],
        "data_cadastro": [
            date(2024, 1, 1) + timedelta(days=rng.randint(0, 600))
            for _ in range(rows)
        ],
    }
    return pa.table(data)


def write_parquet_partitioned(table: pa.Table, base_dir: Path, rows_per_file: int = 50_000) -> int:
    """Writes the table as one or more Parquet files under base_dir."""
    base_dir.mkdir(parents=True, exist_ok=True)
    total = table.num_rows
    files = 0
    for start in range(0, total, rows_per_file):
        end = min(start + rows_per_file, total)
        chunk = table.slice(start, end - start)
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        out = base_dir / f"part-{ts}-{files:04d}.parquet"
        pq.write_table(chunk, out)
        files += 1
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows-pedidos", type=int, default=2000)
    parser.add_argument("--rows-clientes", type=int, default=500)
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 9, 5))
    parser.add_argument("--rows-per-file", type=int, default=50_000)
    args = parser.parse_args()

    pedidos = generate_pedidos(args.rows_pedidos, args.start_date, args.end_date)
    clientes = generate_clientes(args.rows_clientes)

    n_ped = write_parquet_partitioned(pedidos, BRONZE_DIR / "pedidos_vendas", args.rows_per_file)
    n_cli = write_parquet_partitioned(clientes, BRONZE_DIR / "clientes_cadastro", args.rows_per_file)

    print(f"Pedidos: {pedidos.num_rows} rows -> {n_ped} parquet file(s) in {BRONZE_DIR / 'pedidos_vendas'}")
    print(f"Clientes: {clientes.num_rows} rows -> {n_cli} parquet file(s) in {BRONZE_DIR / 'clientes_cadastro'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
