"""
Event producer for simulating streaming data.

Generates synthetic events and publishes them to the file queue.
Can run continuously or in bursts.
"""

import random
import time
import argparse
import signal
import logging
from datetime import datetime, timezone
from typing import List, Optional

from src.streaming.connectors.file_queue import FileQueue, Message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Sample data for generating realistic events
CATEGORIAS = [
    "ELETRONICOS", "MOVEIS", "VESTUARIO", "LIVROS", "BRINQUEDOS",
    "ESPORTE", "BELEZA", "CASA", "JARDIM", "AUTOMOTIVO"
]

FABRICANTES = [
    "TechCorp", "HomeStyle", "FashionWear", "BookWorld", "ToyLand",
    "SportPro", "BeautyPlus", "CasaLar", "JardimVerde", "AutoPeças"
]

STATUS_PEDIDO = ["PENDENTE", "PAGO", "ENVIADO", "ENTREGUE", "CANCELADO"]
STATUS_PAGAMENTO = ["APROVADO", "RECUSADO", "PENDENTE", "ESTORNADO"]


class EventProducer:
    """Produces synthetic events to the file queue."""
    
    def __init__(
        self,
        queue_root: str = "data/streaming/queue",
        num_partitions: int = 4,
    ):
        self.queue = FileQueue(queue_root, num_partitions=num_partitions)
        self._shutdown = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown = True
    
    def generate_pedido(self, pedido_id: int) -> dict:
        """Generate a synthetic pedido event."""
        event_type = random.choice([
            "PEDIDO_CRIADO", "PEDIDO_ATUALIZADO", "PEDIDO_CANCELADO",
            "PAGAMENTO_RECEBIDO", "PAGAMENTO_FALHOU"
        ])
        
        if event_type == "PEDIDO_CRIADO":
            payload = {
                "pedido_id": pedido_id,
                "cliente_id": random.randint(1, 10000),
                "sku_produto": f"SKU-{random.randint(1, 500):03d}",
                "quantidade": random.randint(1, 10),
                "valor_total": round(random.uniform(10.0, 2000.0), 2),
                "status": random.choice(STATUS_PEDIDO),
            }
        elif event_type in ["PEDIDO_ATUALIZADO", "PEDIDO_CANCELADO"]:
            payload = {
                "pedido_id": pedido_id,
                "status_anterior": random.choice(STATUS_PEDIDO),
                "status_novo": random.choice(STATUS_PEDIDO),
            }
        else:  # Pagamento events
            payload = {
                "pedido_id": pedido_id,
                "valor": round(random.uniform(10.0, 2000.0), 2),
                "metodo_pagamento": random.choice(["CARTAO", "PIX", "BOLETO", "TRANSFERENCIA"]),
                "status": random.choice(STATUS_PAGAMENTO),
            }
        
        return {
            "event_id": f"evt_pedido_{pedido_id}_{random.randint(1000, 9999)}",
            "event_type": event_type,
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "source": "event-producer",
            "correlation_id": f"corr_{pedido_id}",
        }
    
    def generate_cliente(self, cliente_id: int) -> dict:
        """Generate a synthetic cliente event."""
        event_type = random.choice([
            "CLIENTE_CRIADO", "CLIENTE_ATUALIZADO", "CLIENTE_DESATIVADO"
        ])
        
        payload = {
            "cliente_id": cliente_id,
            "nome": f"Cliente {cliente_id}",
            "email": f"cliente{cliente_id}@email.com",
            "cpf": f"{random.randint(10000000000, 99999999999):011d}",
            "ativo": event_type != "CLIENTE_DESATIVADO",
        }
        
        if event_type == "CLIENTE_ATUALIZADO":
            payload["campos_alterados"] = random.choice([
                ["email"], ["telefone"], ["endereco"], ["email", "telefone"]
            ])
        
        return {
            "event_id": f"evt_cliente_{cliente_id}_{random.randint(1000, 9999)}",
            "event_type": event_type,
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "source": "event-producer",
            "correlation_id": f"corr_cliente_{cliente_id}",
        }
    
    def generate_produto(self, produto_id: int) -> dict:
        """Generate a synthetic produto event."""
        event_type = random.choice([
            "PRODUTO_CRIADO", "PRODUTO_ATUALIZADO", 
            "PRODUTO_DESATIVADO", "ESTOQUE_ATUALIZADO"
        ])
        
        payload = {
            "produto_id": produto_id,
            "sku_produto": f"SKU-{produto_id:03d}",
            "nome_produto": f"Produto {produto_id}",
            "categoria": random.choice(CATEGORIAS),
            "fabricante": random.choice(FABRICANTES),
            "preco_unitario": round(random.uniform(10.0, 5000.0), 2),
        }
        
        if event_type == "ESTOQUE_ATUALIZADO":
            payload["quantidade_anterior"] = random.randint(0, 500)
            payload["quantidade_nova"] = random.randint(0, 500)
        elif event_type == "PRODUTO_ATUALIZADO":
            payload["campos_alterados"] = random.choice([
                ["preco_unitario"], ["categoria"], ["preco_unitario", "categoria"]
            ])
        
        return {
            "event_id": f"evt_produto_{produto_id}_{random.randint(1000, 9999)}",
            "event_type": event_type,
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "source": "event-producer",
            "correlation_id": f"corr_produto_{produto_id}",
        }
    
    def produce_batch(
        self,
        topic: str,
        count: int,
        start_id: int = 1,
    ) -> List[Message]:
        """Produce a batch of events to a topic."""
        events = []
        
        if topic == "pedidos":
            for i in range(count):
                events.append(self.generate_pedido(start_id + i))
        elif topic == "clientes":
            for i in range(count):
                events.append(self.generate_cliente(start_id + i))
        elif topic == "produtos":
            for i in range(count):
                events.append(self.generate_produto(start_id + i))
        else:
            raise ValueError(f"Unknown topic: {topic}")
        
        produced = self.queue.produce_batch(topic, events)
        logger.info(f"Produced {len(produced)} events to '{topic}'")
        return produced
    
    def run_continuous(
        self,
        topics: List[str] = ["pedidos", "clientes", "produtos"],
        events_per_batch: int = 10,
        interval_seconds: float = 5.0,
        max_events: Optional[int] = None,
    ):
        """Run producer continuously, generating events at regular intervals."""
        logger.info(f"Starting continuous producer for topics: {topics}")
        logger.info(f"Batch size: {events_per_batch}, interval: {interval_seconds}s")
        
        counters = {topic: 1 for topic in topics}
        total_produced = 0
        
        while not self._shutdown:
            try:
                for topic in topics:
                    produced = self.produce_batch(topic, events_per_batch, counters[topic])
                    counters[topic] += events_per_batch
                    total_produced += len(produced)
                    
                    if max_events and total_produced >= max_events:
                        logger.info(f"Reached max events ({max_events}), stopping")
                        return
                
                time.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in producer loop: {e}")
                time.sleep(1.0)
        
        logger.info(f"Producer stopped. Total events: {total_produced}")


def main():
    parser = argparse.ArgumentParser(description="Streaming event producer")
    parser.add_argument("--queue-root", default="data/streaming/queue", help="File queue root")
    parser.add_argument("--topics", nargs="+", default=["pedidos", "clientes", "produtos"])
    parser.add_argument("--batch-size", type=int, default=10, help="Events per batch")
    parser.add_argument("--interval", type=float, default=5.0, help="Interval between batches (seconds)")
    parser.add_argument("--max-events", type=int, help="Max total events to produce")
    parser.add_argument("--partitions", type=int, default=4, help="Number of partitions")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit")
    parser.add_argument("--one-shot", action="store_true", help="Produce one batch and exit")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("Config:")
        print(f"  queue_root: {args.queue_root}")
        print(f"  topics: {args.topics}")
        print(f"  batch_size: {args.batch_size}")
        print(f"  interval: {args.interval}")
        print(f"  max_events: {args.max_events}")
        print(f"  partitions: {args.partitions}")
        print(f"  one_shot: {args.one_shot}")
        return
    
    producer = EventProducer(args.queue_root, num_partitions=args.partitions)
    
    if args.one_shot:
        for topic in args.topics:
            producer.produce_batch(topic, args.batch_size)
    else:
        producer.run_continuous(
            topics=args.topics,
            events_per_batch=args.batch_size,
            interval_seconds=args.interval,
            max_events=args.max_events,
        )


if __name__ == "__main__":
    main()