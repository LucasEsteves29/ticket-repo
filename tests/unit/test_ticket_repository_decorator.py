from datetime import datetime, timezone
from decimal import Decimal

import pytest

from rocketicket.adapters.repository import AuditedTicketRepository
from rocketicket.domain import model
from rocketicket.service_layer import services


def novo_ticket():
    return model.Ticket("t1", "ev1", Decimal("100.00"), "u1")


def test_decorator_preserva_add_get_e_list(fake_ticket_repository):
    registros = []
    repo = AuditedTicketRepository(fake_ticket_repository, registros.append)
    ticket = novo_ticket()

    repo.add(ticket)

    assert repo.get("t1") is ticket
    assert repo.get("ausente") is None
    assert repo.list() == [ticket]
    assert registros == []


def test_checkin_auditado_com_fake(fake_ticket_repository, fake_session):
    ticket = novo_ticket()
    fake_ticket_repository.add(ticket)
    registros = []
    repo = AuditedTicketRepository(fake_ticket_repository, registros.append)
    antes = datetime.now(timezone.utc)

    services.usar_ticket("t1", repo, fake_session)

    assert ticket.status is model.StatusTicket.USADO
    assert fake_session.committed
    assert len(registros) == 1
    assert registros[0].ticket_id == "t1"
    assert registros[0].dono_id == "u1"
    assert antes <= registros[0].ocorrido_em <= datetime.now(timezone.utc)


@pytest.mark.parametrize("status, erro", [
    (model.StatusTicket.USADO, model.TicketJaUsado),
    (model.StatusTicket.ANUNCIADO, model.TicketAnunciado),
    (model.StatusTicket.DISPONIVEL, model.TicketNaoVendido),
])
def test_recusa_nao_gera_auditoria_nem_commit(
    fake_ticket_repository, fake_session, status, erro,
):
    ticket = novo_ticket()
    ticket.status = status
    fake_ticket_repository.add(ticket)
    registros = []
    repo = AuditedTicketRepository(fake_ticket_repository, registros.append)

    with pytest.raises(erro):
        services.usar_ticket("t1", repo, fake_session)

    assert registros == []
    assert not fake_session.committed
    assert ticket.status is status


def test_ticket_ausente_nao_gera_auditoria_nem_commit(
    fake_ticket_repository, fake_session,
):
    registros = []
    repo = AuditedTicketRepository(fake_ticket_repository, registros.append)

    with pytest.raises(services.RecursoNaoEncontrado):
        services.usar_ticket("ausente", repo, fake_session)

    assert registros == []
    assert not fake_session.committed


def test_servico_funciona_sem_decorator(fake_ticket_repository, fake_session):
    ticket = novo_ticket()
    fake_ticket_repository.add(ticket)

    services.usar_ticket("t1", fake_ticket_repository, fake_session)

    assert ticket.status is model.StatusTicket.USADO
    assert fake_session.committed


def test_falha_na_auditoria_nao_confirma_transacao(
    fake_ticket_repository, fake_session,
):
    fake_ticket_repository.add(novo_ticket())

    def falhar(registro):
        raise RuntimeError("auditoria indisponível")

    repo = AuditedTicketRepository(fake_ticket_repository, falhar)
    with pytest.raises(RuntimeError, match="auditoria indisponível"):
        services.usar_ticket("t1", repo, fake_session)

    assert not fake_session.committed
