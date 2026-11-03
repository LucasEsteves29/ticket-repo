from decimal import Decimal

import pytest

from rocketicket.domain.model import StatusTicket, Ticket
from rocketicket.service_layer import services

VALOR = Decimal("100.00")


def novo_ticket(dono_id="u1"):
    return Ticket(id="t1", evento_id="ev1", valor_original=VALOR, dono_id=dono_id)


class TestEmitirTicket:
    def test_emitir_salva_ticket_vendido(self, fake_ticket_repository, fake_session):
        services.emitir_ticket(
            "t1", "ev1", VALOR, "u1", fake_ticket_repository, fake_session
        )

        ticket = fake_ticket_repository.get("t1")
        assert ticket.evento_id == "ev1"
        assert ticket.valor_original == VALOR
        assert ticket.dono_id == "u1"
        assert ticket.status is StatusTicket.VENDIDO

    def test_emitir_faz_commit(self, fake_ticket_repository, fake_session):
        services.emitir_ticket(
            "t1", "ev1", VALOR, "u1", fake_ticket_repository, fake_session
        )

        assert fake_session.committed is True

    def test_emitir_devolve_o_id(self, fake_ticket_repository, fake_session):
        ticket_id = services.emitir_ticket(
            "t1", "ev1", VALOR, "u1", fake_ticket_repository, fake_session
        )

        assert ticket_id == "t1"

    def test_emitir_id_duplicado_falha(self, fake_ticket_repository, fake_session):
        existente = novo_ticket(dono_id="u1")
        fake_ticket_repository.add(existente)

        with pytest.raises(services.TicketJaExiste):
            services.emitir_ticket(
                "t1", "ev2", VALOR, "u2", fake_ticket_repository, fake_session
            )

        assert fake_session.committed is False
        assert fake_ticket_repository.get("t1") is existente
