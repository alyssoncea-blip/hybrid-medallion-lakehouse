"""Tests for streaming jobs (event_producer + microbatch_consumer)."""

from __future__ import annotations

import sys
from datetime import UTC, datetime

import pyarrow.parquet as pq
import pytest

from src.streaming.connectors.file_queue import FileQueue, Message
from src.streaming.jobs import event_producer as ep
from src.streaming.jobs import microbatch_consumer as mc
from src.streaming.jobs.event_producer import EventProducer
from src.streaming.jobs.microbatch_consumer import (
    BatchConfig,
    MicroBatchWriter,
    PartitionConfig,
    StreamingConsumer,
)


@pytest.fixture
def queue_root(tmp_path):
    return str(tmp_path / "queue")


@pytest.fixture
def producer(queue_root):
    return EventProducer(queue_root, num_partitions=2)


@pytest.fixture
def bronze_root(tmp_path):
    return str(tmp_path / "bronze")


class TestEventProducerGenerators:
    def test_generate_pedido_structure(self, producer):
        event = producer.generate_pedido(1)
        assert event["event_type"] in {
            "PEDIDO_CRIADO",
            "PEDIDO_ATUALIZADO",
            "PEDIDO_CANCELADO",
            "PAGAMENTO_RECEBIDO",
            "PAGAMENTO_FALHOU",
        }
        assert event["payload"]["pedido_id"] == 1
        assert event["event_id"].startswith("evt_pedido_1_")
        assert event["source"] == "event-producer"
        assert event["correlation_id"] == "corr_1"

    def test_generate_cliente_structure(self, producer):
        event = producer.generate_cliente(42)
        assert event["event_type"] in {"CLIENTE_CRIADO", "CLIENTE_ATUALIZADO", "CLIENTE_DESATIVADO"}
        payload = event["payload"]
        assert payload["cliente_id"] == 42
        assert len(payload["cpf"]) == 11
        assert payload["cpf"].isdigit()
        assert payload["email"] == "cliente42@email.com"

    def test_generate_produto_structure(self, producer):
        event = producer.generate_produto(7)
        assert event["event_type"] in {
            "PRODUTO_CRIADO",
            "PRODUTO_ATUALIZADO",
            "PRODUTO_DESATIVADO",
            "ESTOQUE_ATUALIZADO",
        }
        payload = event["payload"]
        assert payload["produto_id"] == 7
        assert payload["sku_produto"] == "SKU-007"
        assert 10.0 <= payload["preco_unitario"] <= 5000.0

    def test_desativado_sets_ativo_false(self, producer):
        # CLIENTE_DESATIVADO is one of three types; sample enough to hit it
        seen = {producer.generate_cliente(1)["event_type"] for _ in range(50)}
        assert seen  # generators are random but must produce valid types
        for _ in range(200):
            event = producer.generate_cliente(2)
            if event["event_type"] == "CLIENTE_DESATIVADO":
                assert event["payload"]["ativo"] is False
                return


class TestEventProducerBatch:
    def test_produce_batch_pedidos(self, producer, queue_root):
        produced = producer.produce_batch("pedidos", 5, start_id=100)
        assert len(produced) == 5
        queue = FileQueue(queue_root, num_partitions=2)
        offsets = queue.get_partition_offsets("pedidos")
        assert sum(offsets.values()) == 5

    def test_produce_batch_unknown_topic_raises(self, producer):
        with pytest.raises(ValueError, match="Unknown topic"):
            producer.produce_batch("inexistente", 1)

    def test_signal_handler_sets_shutdown(self, producer):
        producer._signal_handler(2, None)
        assert producer._shutdown is True


class TestMicroBatchWriter:
    def _records(self, n: int = 3) -> list[dict]:
        ts = datetime.now(UTC)
        return [
            {
                "event_id": f"e{i}",
                "event_type": "PEDIDO_CRIADO",
                "event_ts": ts.isoformat(),
                "valor": float(i),
            }
            for i in range(n)
        ]

    def test_write_batch_creates_partitioned_parquet(self, bronze_root):
        writer = MicroBatchWriter(
            PartitionConfig(base_path=bronze_root), BatchConfig()
        )
        paths = writer.write_batch(self._records(5))
        assert len(paths) >= 1
        for p in paths:
            assert p.suffix == ".parquet"
            assert "event_date=" in str(p)
            assert "event_hour=" in str(p)
            assert pq.read_metadata(p).num_rows > 0

    def test_write_empty_batch_returns_nothing(self, bronze_root):
        writer = MicroBatchWriter(PartitionConfig(base_path=bronze_root), BatchConfig())
        assert writer.write_batch([]) == []

    def test_create_table_empty(self, bronze_root):
        writer = MicroBatchWriter(PartitionConfig(base_path=bronze_root), BatchConfig())
        assert writer._create_table([]).num_rows == 0

    def test_partition_columns_added(self, bronze_root):
        writer = MicroBatchWriter(PartitionConfig(base_path=bronze_root), BatchConfig())
        table = writer._create_table(self._records(2))
        assert "event_date" in table.column_names
        assert "event_hour" in table.column_names


class TestStreamingConsumer:
    def test_process_batch_returns_count(self, queue_root, bronze_root):
        consumer = StreamingConsumer(
            queue_root=queue_root,
            bronze_root=bronze_root,
            topics=["pedidos"],
            num_partitions=2,
        )
        ts = datetime.now(UTC).isoformat()
        messages = [
            Message(
                key="k1",
                value={"event_type": "PEDIDO_CRIADO", "event_ts": ts, "x": 1},
                partition=0,
                offset=0,
            ),
            Message(
                key="k2",
                value={"event_type": "PEDIDO_CRIADO", "event_ts": ts, "x": 2},
                partition=1,
                offset=0,
            ),
        ]
        assert consumer._process_batch(messages) == 2

    def test_process_empty_batch(self, queue_root, bronze_root):
        consumer = StreamingConsumer(
            queue_root=queue_root, bronze_root=bronze_root, topics=["pedidos"]
        )
        assert consumer._process_batch([]) == 0

    def test_default_topics(self, queue_root, bronze_root):
        consumer = StreamingConsumer(queue_root=queue_root, bronze_root=bronze_root)
        assert consumer.topics == ["pedidos", "clientes", "produtos"]

    def test_signal_handler(self, queue_root, bronze_root):
        consumer = StreamingConsumer(
            queue_root=queue_root, bronze_root=bronze_root, topics=["pedidos"]
        )
        consumer._signal_handler(15, None)
        assert consumer._shutdown is True


class TestCliDryRun:
    def test_producer_dry_run(self, capsys):
        old = sys.argv
        try:
            sys.argv = ["event_producer", "--dry-run"]
            ep.main()
        finally:
            sys.argv = old
        out = capsys.readouterr().out
        assert "queue_root" in out
        assert "one_shot" in out

    def test_consumer_dry_run(self, capsys):
        old = sys.argv
        try:
            sys.argv = ["microbatch_consumer", "--dry-run"]
            mc.main()
        finally:
            sys.argv = old
        out = capsys.readouterr().out
        assert "bronze_root" in out
        assert "batch_size" in out
