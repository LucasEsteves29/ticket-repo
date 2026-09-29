import pytest
from rocketicket.adapters.repository import (
    AbstractRepository,
    AbstractVendaRepository,
)
from rocketicket.domain import model

# imports dentro das fixtures: os testes unitários não podem carregar o SQLAlchemy


@pytest.fixture
def in_memory_db():
    from sqlalchemy import create_engine

    from rocketicket.adapters import orm

    engine = create_engine("sqlite://")
    orm.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(in_memory_db):
    from sqlalchemy.orm import clear_mappers, sessionmaker

    from rocketicket.adapters import orm

    orm.start_mappers()
    sessao = sessionmaker(bind=in_memory_db)()
    yield sessao
    sessao.close()
    clear_mappers()
    
class FakeTicketRepository(AbstractRepository[model.Ticket]):
    """Implementação em memória do repositório de Ticket."""

    def __init__(self, tickets=None):
        self._tickets = set(tickets or [])

    def add(self, ticket: model.Ticket) -> None:
        self._tickets.add(ticket)

    def get(self, id: str) -> model.Ticket | None:
        return next(
            (ticket for ticket in self._tickets if ticket.id == id),
            None,
        )

    def list(self) -> list[model.Ticket]:
        return sorted(self._tickets, key=lambda ticket: ticket.id)


@pytest.fixture
def fake_ticket_repository():
    return FakeTicketRepository()
    
class FakeVendaRepository(AbstractVendaRepository):
    """Implementação em memória de Venda para uso em testes unitários."""
    def __init__(self, vendas=None):
        self._vendas = set(vendas or [])
    def add(self, venda: model.Venda) -> None:
        self._vendas.add(venda)
    def get(self, id: str) -> model.Venda | None:
        return next((v for v in self._vendas if v.id == id), None)
    def get_ativa_por_ticket(self, ticket_id: str) -> model.Venda | None:
        return next(
            (
                v
                for v in self._vendas
                if v.ticket_id == ticket_id and v.status is model.StatusVenda.ATIVA
            ),
            None,
        )
