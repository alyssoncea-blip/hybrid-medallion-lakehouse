"""
Micro-batch streaming consumer for Bronze layer ingestion.

Reads events from the file-based queue and writes micro-batches
to the Bronze layer as Parquet files, partitioned by date/hour.
"""

import os
import json
import time
import signal
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

from src.streaming.connectors.file_queue import FileQueue, Message
from src.streaming.schemas.events import PedidoEvent, ClienteEvent, ProdutoEvent, Event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for micro-batch processing."""
    batch_size: int = 1000
    batch_timeout_seconds: int = 60
    max_file_size_mb: int = 128
    compression: str = "snappy"


@dataclass
class PartitionConfig:
    """Configuration for output partitioning."""
    partition_cols: List[str] = field(default_factory=lambda: ["event_date", "event_hour"])
    base_path: str = "data/bronze/streaming"


class MicroBatchWriter:
    """Writes micro-batches to Parquet files with partitioning."""
    
    def __init__(self, config: PartitionConfig, batch_config: BatchConfig):
        self.config = config
        self.batch_config = config
        self.base_path = Path(config.base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Current batch state
        self.current_batch: List[Dict[str, Any]] = []
        self.batch_start_time: Optional[float] = None
        self.file_count = 0
    
    def _get_output_path(self, event_ts: datetime) -> Path:
        """Get output path based on event timestamp."""
        date_str = event_ts.strftime("%Y-%m-%d")
        hour_str = event_ts.strftime("%H")
        return self.base_path / f"event_date={date_str}" / f"event_hour={hour_str}"
    
    def _create_table(self, records: List[Dict[str, Any]]) -> pa.Table:
        """Create PyArrow table from records."""
        if not records:
            return pa.Table.from_pydict({})
        
        # Add partitioning columns
        for record in records:
            if "event_ts" in record:
                ts = record["event_ts"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                record["event_date"] = ts.date().isoformat()
                record["event_hour"] = ts.hour
        
        return pa.Table.from_pylist(records)
    
    def write_batch(self, records: List[Dict[str, Any]]) -> List[Path]:
        """Write a batch of records to partitioned Parquet files."""
        if not records:
            return []
        
        table = self._create_table(records)
        if table.num_rows == 0:
            return []
        
        # Partition by date/hour using pyarrow.compute filters
        written_paths = []
        
        # Get unique values for each partition column
        unique_values = {}
        for col in self.config.partition_cols:
            unique_values[col] = table.column(col).unique()
        
        # Generate all combinations of partition values
        import itertools
        partition_combinations = list(itertools.product(*[unique_values[col] for col in self.config.partition_cols]))
        
        for combo in partition_combinations:
            partition_dict = dict(zip(self.config.partition_cols, combo))
            
            # Build filter for this partition
            filter_expr = None
            for col, val in partition_dict.items():
                col_filter = pc.equal(table[col], val)
                if filter_expr is None:
                    filter_expr = col_filter
                else:
                    filter_expr = pc.and_(filter_expr, col_filter)
            
            # Apply filter
            partition_table = table.filter(filter_expr)
            if partition_table.num_rows == 0:
                continue
            
            # Convert PyArrow scalars to Python native types
            def _to_py(val):
                if hasattr(val, 'as_py'):
                    return val.as_py()
                return val
            
            date_val = _to_py(partition_dict.get("event_date", "unknown"))
            hour_val = _to_py(partition_dict.get("event_hour", 0))
            
            output_dir = self.base_path / f"event_date={date_val}" / f"event_hour={hour_val:02d}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            file_name = f"batch_{timestamp}_{self.file_count:04d}.parquet"
            self.file_count += 1
            
            file_path = output_dir / f"{file_name}"
            
            # Drop partition columns from data (they're in directory structure)
            data_table = partition_table.drop(self.config.partition_cols)
            
            pq.write_table(
                data_table,
                file_path,
                compression="snappy",
                use_dictionary=True,
            )
            
            written_paths.append(file_path)
            logger.info(f"Written {partition_table.num_rows} rows to {file_path}")
        
        return written_paths


class StreamingConsumer:
    """
    Micro-batch streaming consumer.
    
    Consumes events from file queue, accumulates into micro-batches,
    and writes to Bronze layer as partitioned Parquet.
    """
    
    def __init__(
        self,
        queue_root: str = "data/streaming/queue",
        bronze_root: str = "data/bronze/streaming",
        topics: Optional[List[str]] = None,
        group_id: str = "bronze-ingestion",
        batch_size: int = 1000,
        batch_timeout_seconds: int = 60,
        num_partitions: int = 4,
        poll_interval_seconds: float = 1.0,
    ):
        self.queue = FileQueue(queue_root, num_partitions=num_partitions)
        self.topics = topics or ["pedidos", "clientes", "produtos"]
        self.group_id = group_id
        
        self.batch_config = BatchConfig(
            batch_size=batch_size,
            batch_timeout_seconds=batch_timeout_seconds,
        )
        
        self.writer = MicroBatchWriter(
            PartitionConfig(base_path=bronze_root),
            self.batch_config,
        )
        
        self.running = False
        self._shutdown = False
        
        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown = True
    
    def _process_batch(self, batch: List[Message]) -> int:
        """Process a batch of messages."""
        if not batch:
            return 0
        
        records = []
        for msg in batch:
            record = msg.value.copy()
            record["_event_id"] = msg.key or f"msg_{msg.offset}"
            record["_event_type"] = record.get("event_type", "UNKNOWN")
            record["_source"] = record.get("source", "unknown")
            record["_partition"] = msg.partition
            record["_offset"] = msg.offset
            record["_ingested_at"] = datetime.now(timezone.utc).isoformat()
            records.append(record)
        
        written_paths = self.writer.write_batch(records)
        logger.info(f"Processed batch of {len(records)} messages -> {len(written_paths)} files")
        return len(records)
    
    def run(self):
        """Main consumer loop."""
        logger.info(f"Starting streaming consumer for topics: {self.topics}")
        logger.info(f"Group ID: {self.group_id}")
        logger.info(f"Batch size: {self.batch_config.batch_size}, timeout: {self.batch_config.batch_timeout_seconds}s")
        
        self.running = True
        
        # Accumulators per topic
        batch_buffers: Dict[str, List[Message]] = {topic: [] for topic in self.topics}
        last_flush_time: Dict[str, float] = {topic: time.time() for topic in self.topics}
        
        while not self._shutdown:
            try:
                for topic in self.topics:
                    # Consume from each partition
                    for partition in range(self.queue.num_partitions):
                        offset = self.queue.get_committed_offset(self.group_id, topic, partition)
                        messages = self.queue.consume(
                            topic, partition, offset, max_messages=self.batch_config.batch_size
                        )
                        
                        if messages:
                            batch_buffers[topic].extend(messages)
                            
                            # Commit offsets
                            for msg in messages:
                                self.queue.commit_offset(
                                    self.group_id, topic, msg.partition, msg.offset + 1
                                )
                
                # Check if any batch is ready to flush
                current_time = time.time()
                for topic in self.topics:
                    buffer = batch_buffers[topic]
                    if not buffer:
                        continue
                    
                    time_elapsed = current_time - last_flush_time[topic]
                    should_flush = (
                        len(buffer) >= self.batch_config.batch_size or
                        time_elapsed >= self.batch_config.batch_timeout_seconds
                    )
                    
                    if should_flush:
                        logger.info(f"Flushing {len(buffer)} messages for topic '{topic}'")
                        self._process_batch(buffer)
                        batch_buffers[topic].clear()
                        last_flush_time[topic] = current_time
                
                # Sleep before next poll
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                time.sleep(5.0)  # Back off on error
        
        # Flush remaining buffers on shutdown
        logger.info("Shutting down, flushing remaining buffers...")
        for topic, buffer in batch_buffers.items():
            if buffer:
                self._process_batch(buffer)
        
        logger.info("Streaming consumer stopped")


def main():
    parser = argparse.ArgumentParser(description="Micro-batch streaming consumer for Bronze layer")
    parser.add_argument("--queue-root", default="data/streaming/queue", help="File queue root directory")
    parser.add_argument("--bronze-root", default="data/bronze/streaming", help="Bronze output root")
    parser.add_argument("--topics", nargs="+", default=["pedidos", "clientes", "produtos"], help="Topics to consume")
    parser.add_argument("--group-id", default="bronze-ingestion", help="Consumer group ID")
    parser.add_argument("--batch-size", type=int, default=1000, help="Micro-batch size")
    parser.add_argument("--batch-timeout", type=int, default=60, help="Batch timeout (seconds)")
    parser.add_argument("--partitions", type=int, default=4, help="Number of partitions")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print(f"Config:")
        print(f"  queue_root: {args.queue_root}")
        print(f"  bronze_root: {args.bronze_root}")
        print(f"  topics: {args.topics}")
        print(f"  group_id: {args.group_id}")
        print(f"  batch_size: {args.batch_size}")
        print(f"  batch_timeout: {args.batch_timeout}")
        print(f"  partitions: {args.partitions}")
        return
    
    consumer = StreamingConsumer(
        queue_root=args.queue_root,
        bronze_root=args.bronze_root,
        topics=args.topics,
        group_id=args.group_id,
        batch_size=args.batch_size,
        batch_timeout_seconds=args.batch_timeout,
        num_partitions=args.partitions,
    )
    
    consumer.run()


if __name__ == "__main__":
    main()