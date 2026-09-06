"""
Event schemas for streaming ingestion.

Defines the contract for events flowing through the streaming pipeline.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class PedidoEvent(BaseModel):
    """Event schema for pedido (order) events."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [{
                "event_id": "evt_abc123",
                "event_type": "PEDIDO_CRIADO",
                "event_ts": "2026-01-15T10:30:00Z",
                "payload": {
                    "pedido_id": 12345,
                    "cliente_id": 678,
                    "sku_produto": "SKU-001",
                    "quantidade": 2,
                    "valor_total": 150.00,
                    "status": "PAGO"
                }
            }]
        }
    )
    
    event_id: str = Field(..., description="Unique event identifier")
    event_type: Literal[
        "PEDIDO_CRIADO",
        "PEDIDO_ATUALIZADO", 
        "PEDIDO_CANCELADO",
        "PAGAMENTO_RECEBIDO",
        "PAGAMENTO_FALHOU"
    ] = Field(..., description="Type of event")
    event_ts: datetime = Field(..., description="Event timestamp (UTC)")
    payload: dict = Field(..., description="Event payload - varies by event_type")
    source: str = Field(default="streaming-api", description="Event source")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")


class ClienteEvent(BaseModel):
    """Event schema for cliente (customer) events."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    event_id: str
    event_type: Literal[
        "CLIENTE_CRIADO",
        "CLIENTE_ATUALIZADO",
        "CLIENTE_DESATIVADO"
    ]
    event_ts: datetime
    payload: dict
    source: str = "streaming-api"
    correlation_id: Optional[str] = None


class ProdutoEvent(BaseModel):
    """Event schema for produto (product) events."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    event_id: str
    event_type: Literal[
        "PRODUTO_CRIADO",
        "PRODUTO_ATUALIZADO",
        "PRODUTO_DESATIVADO",
        "ESTOQUE_ATUALIZADO"
    ]
    event_ts: datetime
    payload: dict
    source: str = "streaming-api"
    correlation_id: Optional[str] = None


# Union of all event types
Event = PedidoEvent | ClienteEvent | ProdutoEvent

# Schema registry for Avro/Parquet
EVENT_SCHEMAS = {
    "pedido": PedidoEvent,
    "cliente": ClienteEvent,
    "produto": ProdutoEvent,
}