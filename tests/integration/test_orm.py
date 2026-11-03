from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from rocketicket.domain.model import StatusTicket, Ticket
from rocketicket.domain.model import StatusVenda, Venda
from rocketicket.domain.model import Pagamento, Pedido, StatusPagamento, StatusPedido

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


PRECO_PADRAO = Decimal("110.00")
VALOR_ORIGINAL_PADRAO = Decimal("100.00")
def nova_venda(preco=PRECO_PADRAO, valor_original=VALOR_ORIGINAL_PADRAO):
    return Venda(
        id="v1",
        ticket_id="t1",
        vendedor_id="u1",
        preco=preco,
        valor_original=valor_original,
    )
class TestMapeamentoVenda:
    def test_venda_salva_volta_campo_a_campo(self, session):
        salvar(session, nova_venda())
        lida = session.get(Venda, "v1")
        assert lida.id == "v1"
        assert lida.ticket_id == "t1"
        assert lida.vendedor_id == "u1"
        assert lida.preco == PRECO_PADRAO
        assert lida.valor_original == VALOR_ORIGINAL_PADRAO
        assert lida.status is StatusVenda.ATIVA
    def test_status_venda_gravado_como_valor_do_enum(self, session):
        salvar(session, nova_venda())
        status = session.execute(text("SELECT status FROM vendas")).scalar_one()
        assert status == "ativa"
    def test_valores_monetarios_voltam_como_decimal(self, session):
        salvar(
            session,
            nova_venda(preco=Decimal("109.98"), valor_original=Decimal("99.99")),
        )
        lida = session.get(Venda, "v1")
        assert isinstance(lida.preco, Decimal)
        assert isinstance(lida.valor_original, Decimal)
        assert lida.preco == Decimal("109.98")
        assert lida.valor_original == Decimal("99.99")
    @pytest.mark.parametrize("status", ["invalido", "ATIVA"])
    def test_banco_recusa_status_venda_fora_do_enum(self, session, status):
        sql = text(
            "INSERT INTO vendas (id, ticket_id, vendedor_id, preco, valor_original, status)"
            " VALUES ('v1', 't1', 'u1', 110.00, 100.00, :status)"
        )
        with pytest.raises(IntegrityError):
            session.execute(sql, {"status": status})
        session.rollback()
        assert session.execute(text("SELECT COUNT(*) FROM vendas")).scalar_one() == 0


VALOR_PEDIDO = Decimal("110.00")


def novo_pedido(valor=VALOR_PEDIDO):
    return Pedido(id="p1", ticket_id="t1", comprador_id="u2", valor=valor)


class TestMapeamentoPedido:
    def test_pedido_salvo_volta_campo_a_campo(self, session):
        salvar(session, novo_pedido())

        lido = session.get(Pedido, "p1")

        assert lido.id == "p1"
        assert lido.ticket_id == "t1"
        assert lido.comprador_id == "u2"
        assert lido.status is StatusPedido.ABERTO

    def test_pagamento_volta_junto_com_o_pedido(self, session):
        salvar(session, novo_pedido())

        lido = session.get(Pedido, "p1")

        assert isinstance(lido.pagamento, Pagamento)
        assert lido.pagamento.valor == VALOR_PEDIDO
        assert lido.pagamento.status is StatusPagamento.PENDENTE

    def test_pagamento_gravado_na_tabela_pagamentos(self, session):
        salvar(session, novo_pedido())

        linha = session.execute(
            text("SELECT pedido_id, valor, status FROM pagamentos")
        ).one()

        assert linha.pedido_id == "p1"
        assert linha.status == "pendente"

    def test_status_gravados_como_valor_do_enum(self, session):
        pedido = novo_pedido()
        pedido.aprovar_pagamento()
        pedido.confirmar(StatusTicket.ANUNCIADO)
        salvar(session, pedido)

        status_pedido = session.execute(text("SELECT status FROM pedidos")).scalar_one()
        status_pagamento = session.execute(
            text("SELECT status FROM pagamentos")
        ).scalar_one()

        assert status_pedido == "confirmado"
        assert status_pagamento == "aprovado"

    def test_valor_do_pagamento_volta_como_decimal(self, session):
        salvar(session, novo_pedido(valor=Decimal("19.99")))

        lido = session.get(Pedido, "p1")

        assert isinstance(lido.pagamento.valor, Decimal)
        assert lido.pagamento.valor == Decimal("19.99")

    @pytest.mark.parametrize("status", ["pago", "ABERTO"])
    def test_banco_recusa_status_pedido_fora_do_enum(self, session, status):
        sql = text(
            "INSERT INTO pedidos (id, ticket_id, comprador_id, status)"
            " VALUES ('p1', 't1', 'u2', :status)"
        )
        with pytest.raises(IntegrityError):
            session.execute(sql, {"status": status})
        session.rollback()

        assert session.execute(text("SELECT COUNT(*) FROM pedidos")).scalar_one() == 0

    @pytest.mark.parametrize("status", ["estornado", "PENDENTE"])
    def test_banco_recusa_status_pagamento_fora_do_enum(self, session, status):
        session.execute(
            text(
                "INSERT INTO pedidos (id, ticket_id, comprador_id, status)"
                " VALUES ('p1', 't1', 'u2', 'aberto')"
            )
        )
        sql = text(
            "INSERT INTO pagamentos (pedido_id, valor, status)"
            " VALUES ('p1', 110.00, :status)"
        )
        with pytest.raises(IntegrityError):
            session.execute(sql, {"status": status})
        session.rollback()

        assert session.execute(text("SELECT COUNT(*) FROM pagamentos")).scalar_one() == 0
