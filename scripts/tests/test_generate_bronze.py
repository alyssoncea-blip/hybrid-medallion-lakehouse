"""Tests for scripts/generate_bronze.py (fixture generator)."""

from __future__ import annotations

import random
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq

from scripts import generate_bronze as gb


class TestRandomCpf:
    def test_length_and_digits(self):
        rng = random.Random(1)
        cpf = gb.random_cpf(rng)
        assert len(cpf) == 11
        assert cpf.isdigit()

    def test_check_digits_valid(self):
        rng = random.Random(42)
        for _ in range(20):
            cpf = gb.random_cpf(rng)
            nums = [int(c) for c in cpf]
            # First check digit
            s = sum(x * (10 - i) for i, x in enumerate(nums[:9]))
            assert (s * 10 % 11) % 10 == nums[9]
            # Second check digit
            s = sum(x * (11 - i) for i, x in enumerate(nums[:10]))
            assert (s * 10 % 11) % 10 == nums[10]


class TestGenerateTables:
    def test_pedidos_shape(self):
        table = gb.generate_pedidos(50, date(2026, 1, 1), date(2026, 6, 30))
        assert table.num_rows == 50
        expected = {
            "pedido_id",
            "cliente_id",
            "data_pedido",
            "valor_total",
            "status",
            "vendedor_id",
            "canal_venda",
        }
        assert set(table.column_names) == expected

    def test_pedidos_deterministic_with_seed(self):
        a = gb.generate_pedidos(20, date(2026, 1, 1), date(2026, 6, 30), seed=7)
        b = gb.generate_pedidos(20, date(2026, 1, 1), date(2026, 6, 30), seed=7)
        assert a.to_pydict() == b.to_pydict()

    def test_clientes_shape(self):
        table = gb.generate_clientes(30)
        assert table.num_rows == 30
        assert set(table.column_names) == {
            "cliente_id",
            "nome",
            "cpf",
            "email",
            "data_cadastro",
        }


class TestWritePartitioned:
    def test_splits_into_multiple_files(self, tmp_path: Path):
        table = gb.generate_pedidos(10, date(2026, 1, 1), date(2026, 2, 1))
        n = gb.write_parquet_partitioned(table, tmp_path, rows_per_file=4)
        assert n == 3  # 10 rows / 4 per file -> 4+4+2
        files = sorted(tmp_path.glob("*.parquet"))
        assert len(files) == 3
        total = sum(pq.read_metadata(f).num_rows for f in files)
        assert total == 10

    def test_empty_table_writes_nothing(self, tmp_path: Path):
        table = gb.generate_pedidos(0, date(2026, 1, 1), date(2026, 1, 2))
        n = gb.write_parquet_partitioned(table, tmp_path)
        assert n == 0
        assert list(tmp_path.glob("*.parquet")) == []
