from decimal import Decimal

from rocketicket.adapters.repository import SqlAlchemyTicketRepository
from rocketicket.domain import model


def novo_ticket(ticket_id: str, dono_id: str = "usuario-1") -> model.Ticket:
    return model.Ticket(
        id=ticket_id,
        evento_id="evento-1",
        valor_original=Decimal("100.00"),
        dono_id=dono_id,
    )


def test_sqlalchemy_repository_adiciona_e_busca_ticket(session):
    repo = SqlAlchemyTicketRepository(session)
    ticket = novo_ticket("ticket-1")

    repo.add(ticket)
    session.commit()
    session.expunge_all()

    encontrado = repo.get("ticket-1")

    assert encontrado is not None
    assert encontrado.id == "ticket-1"
    assert encontrado.evento_id == "evento-1"
    assert encontrado.valor_original == Decimal("100.00")
    assert encontrado.dono_id == "usuario-1"
    assert encontrado.status is model.StatusTicket.VENDIDO


def test_sqlalchemy_repository_retorna_none_para_id_inexistente(session):
    repo = SqlAlchemyTicketRepository(session)

    assert repo.get("ticket-inexistente") is None


def test_sqlalchemy_repository_lista_tickets(session):
    repo = SqlAlchemyTicketRepository(session)
    repo.add(novo_ticket("ticket-2"))
    repo.add(novo_ticket("ticket-1"))
    session.commit()
    session.expunge_all()

    encontrados = repo.list()

    assert [ticket.id for ticket in encontrados] == [
        "ticket-1",
        "ticket-2",
    ]


def test_fake_repository_implementa_o_contrato(fake_ticket_repository):
    primeiro = novo_ticket("ticket-1")
    segundo = novo_ticket("ticket-2")

    fake_ticket_repository.add(primeiro)
    fake_ticket_repository.add(segundo)

    assert fake_ticket_repository.get("ticket-1") is primeiro
    assert fake_ticket_repository.get("ticket-inexistente") is None
    assert [
        ticket.id for ticket in fake_ticket_repository.list()
    ] == ["ticket-1", "ticket-2"]


def test_fake_repository_aceita_tickets_iniciais():
    from conftest import FakeTicketRepository

    ticket = novo_ticket("ticket-inicial")
    repo = FakeTicketRepository([ticket])

    assert repo.get("ticket-inicial") is ticket
