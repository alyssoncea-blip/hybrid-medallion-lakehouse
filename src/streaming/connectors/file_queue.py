"""
File-based message queue for local streaming development.

Simulates a Kafka-like message queue using the filesystem.
Supports partitioning, consumer groups, and offset management.
"""

import os
import json
import time
import uuid
import shutil
from pathlib import Path
from typing import Iterator, Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import threading
import sys

# Cross-platform file locking
if sys.platform == "win32":
    import msvcrt
    def lock_file(f, exclusive=True):
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK if not exclusive else msvcrt.LK_LOCK, 1)
    def unlock_file(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl
    def lock_file(f, exclusive=True):
        fcntl.flock(f, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
    def unlock_file(f):
        fcntl.flock(f, fcntl.LOCK_UN)


@dataclass
class Message:
    """Represents a message in the queue."""
    key: Optional[str]
    value: Dict[str, Any]
    partition: int = 0
    offset: int = -1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    headers: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "partition": self.partition,
            "offset": self.offset,
            "timestamp": self.timestamp.isoformat(),
            "headers": self.headers,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            key=data.get("key"),
            value=data.get("value", {}),
            partition=data.get("partition", 0),
            offset=data.get("offset", -1),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            headers=data.get("headers", {}),
        )


class FileQueue:
    """
    File-based message queue with partitioning.
    
    Directory structure:
    queue_root/
    ├── topic_name/
    │   ├── partition_0/
    │   │   ├── 000000000001.json
    │   │   ├── 000000000002.json
    │   │   └── ...
    │   ├── partition_1/
    │   └── ...
    ├── consumer_offsets/
    │   └── group_name/
    │       └── topic_name/
    │           └── partition_0.offset
    └── .lock/
    
    Features:
    - Append-only log (immutable messages)
    - Partitioning for parallelism
    - Consumer group offsets
    - File locking for thread/process safety
    - Automatic cleanup (retention)
    """
    
    def __init__(
        self,
        root_dir: str = "data/streaming/queue",
        num_partitions: int = 4,
        retention_hours: int = 24,
        max_segment_size_mb: int = 100,
    ):
        self.root = Path(root_dir).resolve()
        self.num_partitions = num_partitions
        self.retention_seconds = retention_hours * 3600
        self.max_segment_bytes = max_segment_size_mb * 1024 * 1024
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        
        # Create directory structure
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "consumer_offsets").mkdir(exist_ok=True)
        (self.root / ".lock").mkdir(exist_ok=True)
        
        # Initialize partitions
        for i in range(num_partitions):
            partition_dir = self.root / f"partition_{i}"
            partition_dir.mkdir(exist_ok=True)
    
    def _get_lock(self, name: str) -> threading.Lock:
        with self._global_lock:
            if name not in self._locks:
                self._locks[name] = threading.Lock()
            return self._locks[name]
    
    def _partition_for_key(self, key: Optional[str]) -> int:
        if key is None:
            return 0
        return abs(hash(key)) % self.num_partitions
    
    def _get_partition_dir(self, topic: str, partition: int) -> Path:
        return self.root / topic / f"partition_{partition}"
    
    def _get_next_offset(self, topic: str, partition: int) -> int:
        partition_dir = self._get_partition_dir(topic, partition)
        partition_dir.mkdir(parents=True, exist_ok=True)
        
        files = sorted(partition_dir.glob("*.json"))
        if not files:
            return 0
        last_file = files[-1]
        return int(last_file.stem) + 1
    
    def produce(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        partition: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Message:
        """Produce a message to the topic."""
        if partition is None:
            partition = self._partition_for_key(key)
        
        if not 0 <= partition < self.num_partitions:
            raise ValueError(f"Partition {partition} out of range [0, {self.num_partitions})")
        
        partition_dir = self._get_partition_dir(topic, partition)
        partition_dir.mkdir(parents=True, exist_ok=True)
        
        lock = self._get_lock(f"produce_{topic}_{partition}")
        with lock:
            offset = self._get_next_offset(topic, partition)
            timestamp = datetime.utcnow()
            
            message = Message(
                key=key,
                value=value,
                partition=partition,
                offset=offset,
                timestamp=timestamp,
                headers=headers or {},
            )
            
            # Write message file
            file_path = partition_dir / f"{offset:012d}.json"
            temp_path = partition_dir / f".{offset:012d}.json.tmp"
            
            with open(temp_path, "w") as f:
                json.dump(message.to_dict(), f, default=str)
            
            # Atomic rename
            temp_path.rename(file_path)
            
            return message
    
    def produce_batch(
        self,
        topic: str,
        messages: List[Dict[str, Any]],
        key_field: Optional[str] = None,
    ) -> List[Message]:
        """Produce multiple messages efficiently."""
        produced = []
        for msg_data in messages:
            key = msg_data.get(key_field) if key_field else None
            msg = self.produce(topic, msg_data, key=key)
            produced.append(msg)
        return produced
    
    def consume(
        self,
        topic: str,
        partition: int,
        offset: int,
        max_messages: int = 100,
        timeout_ms: int = 5000,
    ) -> List[Message]:
        """Consume messages from a partition starting at offset."""
        partition_dir = self._get_partition_dir(topic, partition)
        if not partition_dir.exists():
            return []
        
        messages = []
        files = sorted(partition_dir.glob("*.json"))
        
        for file_path in files:
            file_offset = int(file_path.stem)
            if file_offset < offset:
                continue
            if len(messages) >= max_messages:
                break
            
            try:
                with open(file_path) as f:
                    data = json.load(f)
                msg = Message.from_dict(data)
                messages.append(msg)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        return messages
    
    def get_partition_offsets(self, topic: str) -> Dict[int, int]:
        """Get current end offsets for all partitions of a topic."""
        offsets = {}
        for partition in range(self.num_partitions):
            offsets[partition] = self._get_next_offset(topic, partition)
        return offsets
    
    def commit_offset(
        self,
        group_id: str,
        topic: str,
        partition: int,
        offset: int,
    ) -> None:
        """Commit consumer offset."""
        offset_dir = self.root / "consumer_offsets" / group_id / topic
        offset_dir.mkdir(parents=True, exist_ok=True)
        
        offset_file = offset_dir / f"partition_{partition}.offset"
        lock = self._get_lock(f"offset_{group_id}_{topic}_{partition}")
        
        with lock:
            with open(offset_file, "w") as f:
                f.write(str(offset))
    
    def get_committed_offset(
        self,
        group_id: str,
        topic: str,
        partition: int,
    ) -> int:
        """Get committed offset for consumer group."""
        offset_file = self.root / "consumer_offsets" / group_id / topic / f"partition_{partition}.offset"
        if offset_file.exists():
            with open(offset_file) as f:
                return int(f.read().strip())
        return 0
    
    def get_lag(
        self,
        group_id: str,
        topic: str,
    ) -> Dict[int, int]:
        """Get consumer lag per partition."""
        end_offsets = self.get_partition_offsets(topic)
        lag = {}
        for partition, end_offset in end_offsets.items():
            committed = self.get_committed_offset(group_id, topic, partition)
            lag[partition] = max(0, end_offset - committed)
        return lag
    
    def cleanup_old_segments(self, topic: str) -> int:
        """Remove messages older than retention period."""
        cleaned = 0
        cutoff = time.time() - self.retention_seconds
        
        for partition in range(self.num_partitions):
            partition_dir = self._get_partition_dir(topic, partition)
            if not partition_dir.exists():
                continue
            
            for file_path in partition_dir.glob("*.json"):
                try:
                    mtime = file_path.stat().st_mtime
                    if mtime < cutoff:
                        file_path.unlink()
                        cleaned += 1
                except Exception:
                    pass
        
        return cleaned
    
    @contextmanager
    def consumer(
        self,
        topic: str,
        group_id: str,
        partitions: Optional[List[int]] = None,
        auto_commit: bool = True,
        commit_interval: int = 100,
    ):
        """Context manager for consumer with automatic offset management."""
        if partitions is None:
            partitions = list(range(self.num_partitions))
        
        offsets = {}
        for p in partitions:
            offsets[p] = self.get_committed_offset(group_id, topic, p)
        
        message_count = 0
        
        try:
            yield ConsumerIterator(self, topic, group_id, partitions, offsets, auto_commit, commit_interval)
        finally:
            if auto_commit:
                for partition, offset in offsets.items():
                    self.commit_offset(group_id, topic, partition, offset)


class ConsumerIterator:
    """Iterator for consuming messages with automatic offset tracking."""
    
    def __init__(
        self,
        queue: FileQueue,
        topic: str,
        group_id: str,
        partitions: List[int],
        offsets: Dict[int, int],
        auto_commit: bool,
        commit_interval: int,
    ):
        self.queue = queue
        self.topic = topic
        self.group_id = group_id
        self.partitions = partitions
        self.offsets = offsets
        self.auto_commit = auto_commit
        self.commit_interval = commit_interval
        self.message_count = 0
    
    def __iter__(self):
        return self
    
    def __next__(self):
        # Round-robin across partitions
        for partition in self.partitions:
            offset = self.offsets.get(partition, 0)
            messages = self.queue.consume(
                self.topic, partition, offset, max_messages=1
            )
            if messages:
                msg = messages[0]
                self.offsets[partition] = msg.offset + 1
                self.message_count += 1
                
                # Auto-commit periodically
                if self.auto_commit and self.message_count % self.commit_interval == 0:
                    for p, off in self.offsets.items():
                        self.queue.commit_offset(self.group_id, self.topic, p, off)
                
                return msg
        
        # No messages available
        raise StopIteration
    
    def commit(self):
        """Manually commit current offsets."""
        if self.auto_commit:
            for partition, offset in self.offsets.items():
                self.queue.commit_offset(self.group_id, self.topic, partition, offset)


# Example usage and testing
if __name__ == "__main__":
    # Demo
    queue = FileQueue("data/streaming/queue", num_partitions=2)
    
    # Produce some messages
    print("Producing messages...")
    for i in range(10):
        msg = queue.produce("pedidos", {"pedido_id": i, "valor": i * 10.0}, key=f"pedido_{i}")
        print(f"  Produced: {msg.offset} -> {msg.value}")
    
    # Consume
    print("\nConsuming...")
    with queue.consumer("pedidos", "test-group") as consumer:
        for msg in consumer:
            print(f"  Consumed: offset={msg.offset}, value={msg.value}")
    
    # Check lag
    lag = queue.get_lag("test-group", "pedidos")
    print(f"\nLag: {lag}")