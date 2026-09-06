"""
Unit tests for streaming components.

Run: pytest src/streaming/tests/ -v
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timezone

from src.streaming.connectors.file_queue import FileQueue, Message
from src.streaming.schemas.events import PedidoEvent, ClienteEvent, ProdutoEvent


@pytest.fixture
def temp_queue_root():
    """Create a temporary queue directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield tempfile.mkdtemp()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def queue(temp_queue_root):
    """Create a FileQueue instance for testing."""
    return FileQueue(temp_queue_root, num_partitions=2)


class TestFileQueue:
    def test_produce_and_consume_single(self, queue):
        """Test producing and consuming a single message."""
        topic = "test_topic"
        value = {"event_id": "test_1", "data": "hello"}
        key = "key_1"
        
        msg = queue.produce(topic, value, key=key)
        
        assert msg.key == key
        assert msg.value == value
        # Partition depends on hash of key
        assert msg.partition in [0, 1]
        assert msg.offset == 0
        
        # Consume it back from the correct partition
        messages = queue.consume(topic, msg.partition, 0, max_messages=1)
        assert len(messages) == 1
        assert messages[0].key == key
        assert messages[0].value == value
        assert messages[0].offset == 0
    
    def test_produce_multiple_partitions(self, queue):
        """Test that keys are partitioned consistently."""
        topic = "partition_test"
        
        # Produce messages with same key - should go to same partition
        for i in range(10):
            queue.produce(topic, {"id": i}, key="same_key")
        
        # All should be in same partition
        partition_offsets = queue.get_partition_offsets(topic)
        total_messages = sum(partition_offsets.values())
        assert total_messages == 10
        
        # Find which partition has messages
        active_partition = next(p for p, off in partition_offsets.items() if off > 0)
        assert partition_offsets[active_partition] == 10
    
    def test_different_keys_different_partitions(self, queue):
        """Test that different keys can go to different partitions."""
        topic = "diff_keys"
        
        for i in range(100):
            queue.produce(topic, {"id": i}, key=f"key_{i}")
        
        offsets = queue.get_partition_offsets(topic)
        # With 2 partitions and 100 keys, both should have messages
        active_partitions = sum(1 for off in offsets.values() if off > 0)
        assert active_partitions == 2
    
    def test_consumer_offsets(self, queue):
        """Test consumer offset commit and retrieval."""
        topic = "offset_test"
        group_id = "test_group"
        
        # Produce some messages
        for i in range(5):
            queue.produce(topic, {"id": i})
        
        # Commit offset
        queue.commit_offset(group_id, topic, 0, 3)
        
        # Retrieve committed offset
        committed = queue.get_committed_offset(group_id, topic, 0)
        assert committed == 3
        
        # Get lag
        lag = queue.get_lag(group_id, topic)
        assert lag[0] == 2  # 5 total - 3 committed = 2 lag
    
    def test_consume_from_offset(self, queue):
        """Test consuming from a specific offset."""
        topic = "offset_consume"
        
        # Produce 10 messages
        for i in range(10):
            queue.produce(topic, {"id": i})
        
        # Consume from offset 5
        messages = queue.consume("offset_consume", 0, 5, max_messages=10)
        assert len(messages) == 5
        assert messages[0].offset == 5
        assert messages[-1].offset == 9
    
    def test_produce_batch(self, queue):
        """Test batch production."""
        topic = "batch_test"
        messages = [{"id": i} for i in range(50)]
        
        produced = queue.produce_batch(topic, messages, key_field="id")
        
        assert len(produced) == 50
        offsets = queue.get_partition_offsets(topic)
        assert sum(offsets.values()) == 50
    
    def test_cleanup_old_segments(self, queue):
        """Test cleanup of old segments."""
        topic = "cleanup_test"
        
        # Produce some messages
        for i in range(5):
            queue.produce(topic, {"id": i})
        
        # Manually set old mtime on files
        import time
        partition_dir = queue._get_partition_dir(topic, 0)
        for file_path in partition_dir.glob("*.json"):
            old_time = time.time() - 86400 * 2  # 2 days ago
            import os
            os.utime(file_path, (old_time, old_time))
        
        # Run cleanup with 1 hour retention
        queue.retention_seconds = 3600
        cleaned = queue.cleanup_old_segments(topic)
        
        assert cleaned == 5
        offsets = queue.get_partition_offsets(topic)
        assert offsets[0] == 0  # All cleaned


class TestEventSchemas:
    def test_pedido_event_valid(self):
        """Test PedidoEvent validation."""
        event = PedidoEvent(
            event_id="evt_1",
            event_type="PEDIDO_CRIADO",
            event_ts=datetime.now(timezone.utc),
            payload={"pedido_id": 1, "valor": 100.0},
        )
        assert event.event_type == "PEDIDO_CRIADO"
        assert event.payload["pedido_id"] == 1
    
    def test_pedido_event_invalid_type(self):
        """Test PedidoEvent rejects invalid event_type."""
        with pytest.raises(ValueError):
            PedidoEvent(
                event_id="evt_1",
                event_type="INVALID_TYPE",
                event_ts=datetime.now(timezone.utc),
                payload={},
            )
    
    def test_cliente_event(self):
        """Test ClienteEvent."""
        event = ClienteEvent(
            event_id="evt_c1",
            event_type="CLIENTE_CRIADO",
            event_ts=datetime.now(timezone.utc),
            payload={"cliente_id": 1, "nome": "Teste"},
        )
        assert event.event_type == "CLIENTE_CRIADO"
    
    def test_produto_event(self):
        """Test ProdutoEvent."""
        event = ProdutoEvent(
            event_id="evt_p1",
            event_type="PRODUTO_CRIADO",
            event_ts=datetime.now(timezone.utc),
            payload={"produto_id": 1, "nome": "Produto"},
        )
        assert event.event_type == "PRODUTO_CRIADO"


class TestMessage:
    def test_message_serialization(self):
        """Test Message to/from dict."""
        msg = Message(
            key="test_key",
            value={"data": "test"},
            partition=1,
            offset=42,
            timestamp=datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
            headers={"content-type": "application/json"},
        )
        
        d = msg.to_dict()
        msg2 = Message.from_dict(d)
        
        assert msg2.key == msg.key
        assert msg2.value == msg.value
        assert msg2.partition == msg.partition
        assert msg2.offset == msg.offset
        assert msg2.headers == msg.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])