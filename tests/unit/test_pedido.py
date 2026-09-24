"""Testes unitários do agregado Pedido (com o Pagamento dentro dele).

Nenhum teste atribui pedido.status ou pagamento.status na mão: todos os
estados são alcançados pela API do domínio, para que os testes sobrevivam ao
encapsulamento do agregado na Semana 8.
"""

from decimal import Decimal

import pytest

from rocketicket.domain.model import (
    PagamentoJaProcessado,
    PagamentoNaoAprovado,
    Pedido,
    PedidoEncerrado,
    StatusPagamento,
    StatusPedido,
    StatusTicket,
    TicketIndisponivel,
)

VALOR = Decimal("110.00")


def novo_pedido():
    """Pedido recém-criado, como sairá de criar_pedido() na Semana 4."""
    return Pedido(id="p1", ticket_id="t1", comprador_id="u2", valor=VALOR)


def aprovado():
    """Pedido aberto com pagamento aprovado, pronto para ser confirmado."""
    pedido = novo_pedido()
    pedido.aprovar_pagamento()
    return pedido


def confirmado():
    """Pedido confirmado — estado final."""
    pedido = aprovado()
    pedido.confirmar(StatusTicket.ANUNCIADO)
    return pedido


def cancelado():
    """Pedido cancelado — estado final."""
    pedido = novo_pedido()
    pedido.cancelar()
    return pedido


class TestCriacao:
    def test_pedido_nasce_aberto_com_pagamento_pendente(self):
        pedido = novo_pedido()
        assert pedido.status is StatusPedido.ABERTO
        assert pedido.pagamento.status is StatusPagamento.PENDENTE

    def test_pagamento_nasce_com_o_valor_do_pedido(self):
        assert novo_pedido().pagamento.valor == VALOR


class TestPagamento:
    def test_aprovar_pagamento(self):
        pedido = novo_pedido()
        pedido.aprovar_pagamento()
        assert pedido.pagamento.status is StatusPagamento.APROVADO
        assert pedido.status is StatusPedido.ABERTO

    def test_recusar_pagamento(self):
        pedido = novo_pedido()
        pedido.recusar_pagamento()
        assert pedido.pagamento.status is StatusPagamento.RECUSADO
        assert pedido.status is StatusPedido.ABERTO

    def test_aprovar_pagamento_ja_recusado_falha(self):
        pedido = novo_pedido()
        pedido.recusar_pagamento()
        with pytest.raises(PagamentoJaProcessado):
            pedido.aprovar_pagamento()

    def test_recusar_pagamento_ja_aprovado_falha(self):
        pedido = aprovado()
        with pytest.raises(PagamentoJaProcessado):
            pedido.recusar_pagamento()

    def test_alterar_pagamento_de_pedido_confirmado_falha(self):
        pedido = confirmado()
        with pytest.raises(PedidoEncerrado):
            pedido.recusar_pagamento()
        assert pedido.pagamento.status is StatusPagamento.APROVADO

    def test_alterar_pagamento_de_pedido_cancelado_falha(self):
        pedido = cancelado()
        with pytest.raises(PedidoEncerrado):
            pedido.aprovar_pagamento()
        assert pedido.pagamento.status is StatusPagamento.PENDENTE


class TestConfirmar:
    def test_confirmar_com_pagamento_aprovado_e_ticket_anunciado(self):
        pedido = aprovado()
        pedido.confirmar(StatusTicket.ANUNCIADO)
        assert pedido.status is StatusPedido.CONFIRMADO

    def test_confirmar_com_pagamento_pendente_falha(self):
        pedido = novo_pedido()
        with pytest.raises(PagamentoNaoAprovado):
            pedido.confirmar(StatusTicket.ANUNCIADO)

    def test_confirmar_com_pagamento_recusado_falha(self):
        pedido = novo_pedido()
        pedido.recusar_pagamento()
        with pytest.raises(PagamentoNaoAprovado):
            pedido.confirmar(StatusTicket.ANUNCIADO)

    @pytest.mark.parametrize(
        "status_ticket",
        [StatusTicket.VENDIDO, StatusTicket.USADO, StatusTicket.DISPONIVEL],
    )
    def test_confirmar_com_ticket_nao_anunciado_falha(self, status_ticket):
        # DISPONIVEL entra aqui de propósito: "disponível" é ANUNCIADO.
        pedido = aprovado()
        with pytest.raises(TicketIndisponivel):
            pedido.confirmar(status_ticket)
        assert pedido.status is StatusPedido.ABERTO

    def test_confirmar_pedido_ja_confirmado_falha(self):
        pedido = confirmado()
        with pytest.raises(PedidoEncerrado):
            pedido.confirmar(StatusTicket.ANUNCIADO)

    def test_confirmar_pedido_cancelado_falha(self):
        pedido = cancelado()
        with pytest.raises(PedidoEncerrado):
            pedido.confirmar(StatusTicket.ANUNCIADO)


class TestCancelar:
    def test_cancelar_pedido_aberto(self):
        assert cancelado().status is StatusPedido.CANCELADO

    def test_cancelar_pedido_com_pagamento_recusado(self):
        pedido = novo_pedido()
        pedido.recusar_pagamento()
        pedido.cancelar()
        assert pedido.status is StatusPedido.CANCELADO

    def test_cancelar_pedido_ja_cancelado_falha(self):
        pedido = cancelado()
        with pytest.raises(PedidoEncerrado):
            pedido.cancelar()

    def test_cancelar_pedido_confirmado_falha(self):
        pedido = confirmado()
        with pytest.raises(PedidoEncerrado):
            pedido.cancelar()
        assert pedido.status is StatusPedido.CONFIRMADO
