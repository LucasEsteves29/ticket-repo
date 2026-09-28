from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from rocketicket.domain.model import StatusTicket, Ticket

VALOR = Decimal("150.00")


def novo_ticket(valor=VALOR):
    return Ticket(id="t1", evento_id="ev1", valor_original=valor, dono_id="u1")


def salvar(session, ticket):
    session.add(ticket)
    session.commit()
    session.expunge_all()


class TestMapeamentoTicket:
    def test_ticket_salvo_volta_campo_a_campo(self, session):
        salvar(session, novo_ticket())

        lido = session.get(Ticket, "t1")

        assert lido.id == "t1"
        assert lido.evento_id == "ev1"
        assert lido.valor_original == VALOR
        assert lido.dono_id == "u1"
        assert lido.status is StatusTicket.VENDIDO

    def test_status_gravado_como_valor_do_enum(self, session):
        salvar(session, novo_ticket())

        status = session.execute(text("SELECT status FROM tickets")).scalar_one()

        assert status == "vendido"

    def test_valor_original_volta_como_decimal(self, session):
        salvar(session, novo_ticket(valor=Decimal("19.99")))

        lido = session.get(Ticket, "t1")

        assert isinstance(lido.valor_original, Decimal)
        assert lido.valor_original == Decimal("19.99")

    @pytest.mark.parametrize("status", ["cancelado", "VENDIDO"])
    def test_banco_recusa_status_fora_do_enum(self, session, status):
        sql = text(
            "INSERT INTO tickets (id, evento_id, valor_original, dono_id, status)"
            " VALUES ('t1', 'ev1', 150, 'u1', :status)"
        )
        with pytest.raises(IntegrityError):
            session.execute(sql, {"status": status})
        session.rollback()

        assert session.execute(text("SELECT COUNT(*) FROM tickets")).scalar_one() == 0
