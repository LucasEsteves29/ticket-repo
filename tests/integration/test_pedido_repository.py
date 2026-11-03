"""Testes de integração do SqlAlchemyPedidoRepository contra SQLite em memória."""

from decimal import Decimal

from sqlalchemy import text

from rocketicket.adapters.repository import SqlAlchemyPedidoRepository
from rocketicket.domain.model import (
    Pedido,
    StatusPagamento,
    StatusPedido,
    StatusTicket,
)

VALOR = Decimal("110.00")


def novo_pedido(id="p1"):
    return Pedido(id=id, ticket_id="t1", comprador_id="u2", valor=VALOR)


def test_add_grava_pedido_e_pagamento(session):
    repo = SqlAlchemyPedidoRepository(session)

    repo.add(novo_pedido())
    session.commit()

    pedidos = session.execute(
        text("SELECT id, ticket_id, comprador_id, status FROM pedidos")
    ).all()
    pagamentos = session.execute(
        text("SELECT pedido_id, valor, status FROM pagamentos")
    ).all()
    assert pedidos == [("p1", "t1", "u2", "aberto")]
    assert [(p.pedido_id, Decimal(str(p.valor)), p.status) for p in pagamentos] == [
        ("p1", VALOR, "pendente")
    ]


def test_add_nao_faz_commit(session):
    repo = SqlAlchemyPedidoRepository(session)

    repo.add(novo_pedido())
    session.rollback()

    assert session.execute(text("SELECT COUNT(*) FROM pedidos")).scalar_one() == 0
    assert session.execute(text("SELECT COUNT(*) FROM pagamentos")).scalar_one() == 0


def test_get_devolve_pedido_com_pagamento(session):
    session.execute(
        text(
            "INSERT INTO pedidos (id, ticket_id, comprador_id, status)"
            " VALUES ('p1', 't1', 'u2', 'aberto')"
        )
    )
    session.execute(
        text(
            "INSERT INTO pagamentos (pedido_id, valor, status)"
            " VALUES ('p1', 110.00, 'aprovado')"
        )
    )
    repo = SqlAlchemyPedidoRepository(session)

    pedido = repo.get("p1")

    assert pedido == novo_pedido()
    assert pedido.status is StatusPedido.ABERTO
    assert pedido.pagamento.valor == VALOR
    assert pedido.pagamento.status is StatusPagamento.APROVADO


def test_get_devolve_none_se_nao_existe(session):
    repo = SqlAlchemyPedidoRepository(session)

    assert repo.get("nao-existe") is None


def test_mudancas_de_estado_persistem_apos_commit(session):
    repo = SqlAlchemyPedidoRepository(session)
    repo.add(novo_pedido())
    session.commit()

    pedido = repo.get("p1")
    pedido.aprovar_pagamento()
    pedido.confirmar(StatusTicket.ANUNCIADO)
    session.commit()
    session.expunge_all()

    lido = repo.get("p1")
    assert lido.status is StatusPedido.CONFIRMADO
    assert lido.pagamento.status is StatusPagamento.APROVADO


def test_get_distingue_pedidos(session):
    repo = SqlAlchemyPedidoRepository(session)
    repo.add(novo_pedido("p1"))
    repo.add(novo_pedido("p2"))
    session.commit()
    session.expunge_all()

    assert repo.get("p2").id == "p2"
    assert repo.get("p1").id == "p1"
