"""Repositórios do RocketTicket: a porta entre o domínio e a persistência.

O repositório só guarda e busca a raiz do agregado. Ele NUNCA faz commit:
quem confirma a transação é o chamador (teste -> service -> UoW).

As versões falsas (Fake*Repository), usadas nos testes unitários, ficam em
tests/conftest.py.
"""

import abc
from typing import Generic, TypeVar

from rocketicket.domain import model

T = TypeVar("T")


class AbstractRepository(abc.ABC, Generic[T]):
    """Contrato mínimo de todo repositório: add() e get() da raiz do agregado.

    Uma consulta a mais de um agregado ganha abstração própria, herdando desta,
    para que o Fake também seja obrigado a implementá-la.
    """

    @abc.abstractmethod
    def add(self, agregado: T) -> None:
        """Passa a acompanhar o agregado; ele só vai para o banco no commit do chamador."""
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, id: str) -> T | None:
        """Devolve o agregado com esse id, ou None se ele não existir."""
        raise NotImplementedError


# Ticket — Caio
class SqlAlchemyTicketRepository(AbstractRepository[model.Ticket]):
    """Persistência de tickets usando uma sessão SQLAlchemy."""

    def __init__(self, session):
        self.session = session

    def add(self, ticket: model.Ticket) -> None:
        self.session.add(ticket)

    def get(self, id: str) -> model.Ticket | None:
        return self.session.get(model.Ticket, id)

    def list(self) -> list[model.Ticket]:
        return (
            self.session.query(model.Ticket)
            .order_by(model.Ticket.id)
            .all()
        )

# Venda — Miguel


class AbstractVendaRepository(AbstractRepository[model.Venda]):
    """
    Repositorio de Venda: além de add() e get(), acha o anúncio ativo de um ticket.

    É por aqui que criar_anuncio descobe se o ticket já tem um anúncio ATIVA
    antes de abrir outro.
    """

    @abc.abstractmethod
    def get_ativa_por_ticket(self, ticket_id: str) -> model.Venda | None:
        """Devolve a venda ATIVA desse ticket, ou None se ele não estiver anunciado."""
        raise NotImplementedError


class SqlAlchemyVendaRepository(AbstractVendaRepository):
    """Venda persistida com SQLAlchemy.

    Recebe a sessão pronta e não importa o SQLAlchemy: o conftest.py importa este
    módulo, e os testes unitários não podem carregar o banco. Não faz commit.
    """

    def __init__(self, session):
        self.session = session

    def add(self, venda: model.Venda) -> None:
        self.session.add(venda)

    def get(self, id: str) -> model.Venda | None:
        return self.session.get(model.Venda, id)

    def get_ativa_por_ticket(self, ticket_id: str) -> model.Venda | None:
        return (
            self.session.query(model.Venda)
            .filter_by(ticket_id=ticket_id, status=model.StatusVenda.ATIVA)
            .first()
        )


# Pedido — Guilherme
# Repositório concreto de model.Pedido, herdando AbstractRepository[model.Pedido].
