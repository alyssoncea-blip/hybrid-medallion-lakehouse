# Streaming Ingestion for Hybrid Medallion Lakehouse

This directory contains a **local-first streaming pipeline** that simulates event ingestion from Kafka-like sources into the Bronze layer using a file-based message queue.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Producers  │────▶│  File Queue      │────▶│  Micro-batch    │
│  (Simulated)│     │  (Local Kafka)   │     │  Consumer       │
└─────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │  Bronze Layer   │
                                                │  (Parquet)      │
                                                └─────────────────┘
```

## Components

| Component | File | Description |
|-----------|------|-------------|
| **Event Schemas** | `schemas/events.py` | Pydantic models for Pedido, Cliente, Produto events |
| **File Queue** | `connectors/file_queue.py` | Local Kafka-like queue using filesystem |
| **Event Producer** | `jobs/event_producer.py` | Generates synthetic events |
| **Micro-batch Consumer** | `jobs/microbatch_consumer.py` | Consumes queue → writes Bronze Parquet |

## Quick Start

### 1. Install Dependencies
```bash
pip install -r src/streaming/requirements.txt
```

### 2. Start Event Producer (Terminal 1)
```bash
# Continuous producer (generates events every 5 seconds)
python src/streaming/jobs/event_producer.py \
    --topics pedidos clientes produtos \
    --batch-size 50 \
    --interval 5.0

# One-shot producer (single batch)
python src/streaming/jobs/event_producer.py \
    --topics pedidos \
    --batch-size 100 \
    --one-shot
```

### 3. Start Micro-batch Consumer (Terminal 2)
```bash
python src/streaming/jobs/microbatch_consumer.py \
    --topics pedidos clientes produtos \
    --group-id bronze-ingestion \
    --batch-size 1000 \
    --batch-timeout 60
```

### 4. Verify Bronze Output
```bash
# Check generated Parquet files
find data/bronze/streaming -name "*.parquet" | head -5

# Inspect with DuckDB
duckdb -c "
SELECT * FROM read_parquet('data/bronze/streaming/**/*.parquet') 
LIMIT 10;
"
```

## File Queue Design

The `FileQueue` class provides a **local Kafka alternative** using the filesystem:

### Features
- **Partitioning** — Configurable partitions (default: 4) for parallelism
- **Offsets** — Per-partition offsets with consumer group support
- **Ordering** — Messages within a partition are strictly ordered
- **Durability** — Atomic writes with fsync, crash-safe
- **Retention** — Automatic cleanup of old segments (configurable TTL)
- **Thread-safe** — File locking for concurrent producers/consumers

### Directory Structure
```
data/streaming/queue/
├── pedidos/
│   ├── partition_0/
│   │   ├── 000000000001.json
│   │   └── 000000000002.json
│   └── partition_1/
├── clientes/
│   └── ...
├── consumer_offsets/
│   └── bronze-ingestion/
│       └── pedidos/
│           ├── partition_0.offset
│           └── partition_1.offset
└── .lock/
```

## Event Types

### Pedido Events
```json
{
  "event_id": "evt_pedido_123_4567",
  "event_type": "PEDIDO_CRIADO",
  "event_ts": "2026-01-15T10:30:00Z",
  "payload": {
    "pedido_id": 12345,
    "cliente_id": 678,
    "sku_produto": "SKU-001",
    "quantidade": 2,
    "valor_total": 150.00,
    "status": "PAGO"
  },
  "source": "event-producer",
  "correlation_id": "corr_12345"
}
```

### Supported Event Types
| Topic | Event Types |
|-------|-------------|
| `pedidos` | PEDIDO_CRIADO, PEDIDO_ATUALIZADO, PEDIDO_CANCELADO, PAGAMENTO_RECEBIDO, PAGAMENTO_FALHOU |
| `clientes` | CLIENTE_CRIADO, CLIENTE_ATUALIZADO, CLIENTE_DESATIVADO |
| `produtos` | PRODUTO_CRIADO, PRODUTO_ATUALIZADO, PRODUTO_DESATIVADO, ESTOQUE_ATUALIZADO |

## Micro-batch Consumer Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `batch_size` | 1000 | Max messages per micro-batch |
| `batch_timeout_seconds` | 60 | Max time to wait before flushing |
| `num_partitions` | 4 | Queue partitions (must match producer) |
| `poll_interval_seconds` | 1.0 | Polling interval |

### Output Partitioning
Bronze files are partitioned by:
- `event_date` (YYYY-MM-DD)
- `event_hour` (0-23)

```
data/bronze/streaming/
├── event_date=2026-01-15/
│   ├── event_hour=10/
│   │   ├── batch_20260115_103000_0001.parquet
│   │   └── batch_20260115_103005_0002.parquet
│   └── event_hour=11/
└── event_date=2026-01-16/
    └── ...
```

## Running in Airflow

The `src/airflow/dags/hybrid_medallion_lakehouse_dbt.py` DAG can be extended to orchestrate streaming:

```python
from airflow.operators.bash import BashOperator

run_streaming_consumer = BashOperator(
    task_id="streaming_consumer",
    bash_command="""
        cd /opt/airflow &&
        timeout 3600 python src/streaming/jobs/microbatch_consumer.py \
            --topics pedidos clientes produtos \
            --group-id bronze-ingestion \
            --batch-size 1000 \
            --batch-timeout 60
    """,
    # Run daily, or as a long-running service
)
```

## Production Considerations

For production, replace `FileQueue` with:
- **Apache Kafka** + `confluent-kafka` Python client
- **Redpanda** (Kafka-compatible, simpler)
- **Apache Pulsar**
- **AWS Kinesis** / **Google Pub/Sub** / **Azure Event Hubs**

The `FileQueue` interface is designed to be swappable — just implement the same `produce/consume/commit_offset` methods.

## Testing

```bash
# Run unit tests
python -m pytest src/streaming/tests/ -v

# Test producer/consumer locally
python src/streaming/jobs/event_producer.py --dry-run
python src/streaming/jobs/microbatch_consumer.py --dry-run
```