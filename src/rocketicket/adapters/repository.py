"""Repositórios do RocketTicket: a porta entre o domínio e a persistência.

O repositório só guarda e busca a raiz do agregado. Ele NUNCA faz commit:
quem confirma a transação é o chamador (teste -> service -> UoW).

As versões falsas (Fake*Repository), usadas nos testes unitários, ficam em
tests/conftest.py.
"""

import abc
from typing import Generic, TypeVar

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
# Repositório concreto de model.Ticket, herdando AbstractRepository[model.Ticket].


# Venda — Miguel
# AbstractVendaRepository(AbstractRepository[model.Venda]), que acrescenta
# get_ativa_por_ticket(ticket_id), e o repositório concreto que a implementa.


# Pedido — Guilherme
# Repositório concreto de model.Pedido, herdando AbstractRepository[model.Pedido].
