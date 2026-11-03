"""Mapeamento objeto-relacional do RocketTicket.

Mapeamento imperativo: as tabelas moram aqui e o domínio não sabe que existe
banco (model.py NUNCA importa SQLAlchemy). Cada agregado tem suas tabelas e
uma função _mapear_<agregado>(), chamada por start_mappers().

Regras de todas as tabelas: a PK é o id do domínio, as colunas são NOT NULL,
dinheiro é Numeric(10, 2) (nunca Float) e não há FK entre agregados (FK
dentro do mesmo agregado, como pagamentos -> pedidos, é permitida).
"""

from sqlalchemy import Column, Enum, ForeignKey, MetaData, Numeric, String, Table
from sqlalchemy.orm import registry, relationship

from rocketicket.domain import model

metadata = MetaData()
mapper_registry = registry(metadata=metadata)


def _enum_por_valor(enum_cls):
    """Tipo de coluna que grava o valor do enum ("vendido"), não o nome ("VENDIDO").

    native_enum=False vira VARCHAR com CHECK (create_constraint=True), igual em
    qualquer banco; validate_strings=True recusa string fora do enum antes de
    chegar ao banco.
    """
    return Enum(
        enum_cls,
        values_callable=lambda cls: [membro.value for membro in cls],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


# Ticket — Lucas

tickets = Table(
    "tickets",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("evento_id", String(255), nullable=False),
    Column("valor_original", Numeric(10, 2), nullable=False),
    Column("dono_id", String(255), nullable=False),
    Column("status", _enum_por_valor(model.StatusTicket), nullable=False),
)


def _mapear_ticket() -> None:
    mapper_registry.map_imperatively(model.Ticket, tickets)


# Venda — Igor

vendas = Table(
    "vendas",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("ticket_id", String(255), nullable=False),
    Column("vendedor_id", String(255), nullable=False),
    Column("preco", Numeric(10, 2), nullable=False),
    Column("valor_original", Numeric(10, 2), nullable=False),
    Column("status", _enum_por_valor(model.StatusVenda), nullable=False),
)
def _mapear_venda() -> None:
    mapper_registry.map_imperatively(model.Venda, vendas)

# Pedido — Guilherme
#
# O Pagamento não tem id no domínio: ele é do Pedido e só existe dentro dele.
# Por isso a PK de pagamentos é o próprio pedido_id (1:1), e a FK é permitida
# porque liga duas tabelas do MESMO agregado.

pedidos = Table(
    "pedidos",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("ticket_id", String(255), nullable=False),
    Column("comprador_id", String(255), nullable=False),
    Column("status", _enum_por_valor(model.StatusPedido), nullable=False),
)

pagamentos = Table(
    "pagamentos",
    metadata,
    Column("pedido_id", String(255), ForeignKey("pedidos.id"), primary_key=True),
    Column("valor", Numeric(10, 2), nullable=False),
    Column("status", _enum_por_valor(model.StatusPagamento), nullable=False),
)


def _mapear_pedido() -> None:
    mapper_registry.map_imperatively(model.Pagamento, pagamentos)
    mapper_registry.map_imperatively(
        model.Pedido,
        pedidos,
        properties={
            # Salvar/apagar o Pedido leva o Pagamento junto: ele não tem vida própria.
            "pagamento": relationship(
                model.Pagamento,
                uselist=False,
                lazy="joined",
                cascade="all, delete-orphan",
            ),
        },
    )


def start_mappers() -> None:
    """Liga cada classe do domínio à sua tabela.

    Uma vez por processo; nos testes, uma vez por fixture, com clear_mappers()
    """
    _mapear_ticket()
    _mapear_venda()
    _mapear_pedido()