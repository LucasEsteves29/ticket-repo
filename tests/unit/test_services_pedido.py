from decimal import Decimal

import pytest

from rocketicket.domain import model
from rocketicket.domain.model import StatusPagamento, StatusPedido, Ticket, Venda
from rocketicket.service_layer import services

VALOR_ORIGINAL = Decimal("100.00")
PRECO_ANUNCIO = Decimal("105.00")


def novo_anuncio():
    return Venda(
        id="v1",
        ticket_id="t1",
        vendedor_id="u1",
        preco=PRECO_ANUNCIO,
        valor_original=VALOR_ORIGINAL,
    )


def ticket_anunciado():
    ticket = Ticket(id="t1", evento_id="ev1", valor_original=VALOR_ORIGINAL, dono_id="u1")
    ticket.anunciar()
    return ticket


def novo_pedido():
    return model.Pedido(id="p1", ticket_id="t1", comprador_id="u2", valor=PRECO_ANUNCIO)


class TestCriarPedido:
    def test_criar_salva_pedido_aberto_com_pagamento_pendente(
        self, fake_pedido_repository, fake_venda_repository, fake_session
    ):
        fake_venda_repository.add(novo_anuncio())

        pedido_id = services.criar_pedido(
            "p1", "t1", "u2", fake_pedido_repository, fake_venda_repository, fake_session
        )

        assert pedido_id == "p1"
        pedido = fake_pedido_repository.get("p1")
        assert pedido.ticket_id == "t1"
        assert pedido.comprador_id == "u2"
        assert pedido.status is StatusPedido.ABERTO
        assert pedido.pagamento.status is StatusPagamento.PENDENTE
        assert fake_session.committed is True

    def test_valor_do_pedido_vem_do_preco_do_anuncio(
        self, fake_pedido_repository, fake_venda_repository, fake_session
    ):
        fake_venda_repository.add(novo_anuncio())

        services.criar_pedido(
            "p1", "t1", "u2", fake_pedido_repository, fake_venda_repository, fake_session
        )

        assert fake_pedido_repository.get("p1").pagamento.valor == PRECO_ANUNCIO

    def test_ticket_sem_anuncio_lanca_recurso_nao_encontrado(
        self, fake_pedido_repository, fake_venda_repository, fake_session
    ):
        with pytest.raises(services.RecursoNaoEncontrado):
            services.criar_pedido(
                "p1", "t1", "u2", fake_pedido_repository, fake_venda_repository, fake_session
            )

        assert fake_pedido_repository.get("p1") is None
        assert fake_session.committed is False

    def test_anuncio_cancelado_nao_aceita_pedido(
        self, fake_pedido_repository, fake_venda_repository, fake_session
    ):
        anuncio = novo_anuncio()
        anuncio.cancelar()
        fake_venda_repository.add(anuncio)

        with pytest.raises(services.RecursoNaoEncontrado):
            services.criar_pedido(
                "p1", "t1", "u2", fake_pedido_repository, fake_venda_repository, fake_session
            )

        assert fake_session.committed is False

    def test_id_repetido_lanca_pedido_ja_existe(
        self, fake_pedido_repository, fake_venda_repository, fake_session
    ):
        fake_pedido_repository.add(novo_pedido())
        fake_venda_repository.add(novo_anuncio())

        with pytest.raises(services.PedidoJaExiste):
            services.criar_pedido(
                "p1", "t1", "u3", fake_pedido_repository, fake_venda_repository, fake_session
            )

        assert fake_pedido_repository.get("p1").comprador_id == "u2"
        assert fake_session.committed is False


class TestConfirmarPedido:
    def test_pagamento_aprovado_confirma_o_pedido(
        self, fake_pedido_repository, fake_ticket_repository, fake_session
    ):
        fake_pedido_repository.add(novo_pedido())
        fake_ticket_repository.add(ticket_anunciado())

        services.confirmar_pedido(
            "p1", True, fake_pedido_repository, fake_ticket_repository, fake_session
        )

        pedido = fake_pedido_repository.get("p1")
        assert pedido.status is StatusPedido.CONFIRMADO
        assert pedido.pagamento.status is StatusPagamento.APROVADO
        assert fake_session.committed is True

    def test_pagamento_recusado_e_salvo_e_pedido_fica_aberto(
        self, fake_pedido_repository, fake_ticket_repository, fake_session
    ):
        fake_pedido_repository.add(novo_pedido())
        fake_ticket_repository.add(ticket_anunciado())

        services.confirmar_pedido(
            "p1", False, fake_pedido_repository, fake_ticket_repository, fake_session
        )

        pedido = fake_pedido_repository.get("p1")
        assert pedido.status is StatusPedido.ABERTO
        assert pedido.pagamento.status is StatusPagamento.RECUSADO
        assert fake_session.committed is True

    def test_pagamento_recusado_nao_pode_ser_aprovado_depois(
        self, fake_pedido_repository, fake_ticket_repository, fake_session
    ):
        fake_pedido_repository.add(novo_pedido())
        fake_ticket_repository.add(ticket_anunciado())
        services.confirmar_pedido(
            "p1", False, fake_pedido_repository, fake_ticket_repository, fake_session
        )

        with pytest.raises(model.PagamentoJaProcessado):
            services.confirmar_pedido(
                "p1", True, fake_pedido_repository, fake_ticket_repository, fake_session
            )

        assert fake_pedido_repository.get("p1").status is StatusPedido.ABERTO

    def test_ticket_nao_anunciado_lanca_ticket_indisponivel(
        self, fake_pedido_repository, fake_ticket_repository, fake_session
    ):
        ticket = ticket_anunciado()
        ticket.retirar_anuncio()
        fake_pedido_repository.add(novo_pedido())
        fake_ticket_repository.add(ticket)

        with pytest.raises(model.TicketIndisponivel):
            services.confirmar_pedido(
                "p1", True, fake_pedido_repository, fake_ticket_repository, fake_session
            )

        assert fake_pedido_repository.get("p1").status is StatusPedido.ABERTO
        assert fake_session.committed is False

    def test_ticket_usado_lanca_ticket_indisponivel(
        self, fake_pedido_repository, fake_ticket_repository, fake_session
    ):
        ticket = ticket_anunciado()
        ticket.retirar_anuncio()
        ticket.usar()
        fake_pedido_repository.add(novo_pedido())
        fake_ticket_repository.add(ticket)

        with pytest.raises(model.TicketIndisponivel):
            services.confirmar_pedido(
                "p1", True, fake_pedido_repository, fake_ticket_repository, fake_session
            )

        assert fake_session.committed is False

    def test_pedido_inexistente_lanca_recurso_nao_encontrado(
        self, fake_pedido_repository, fake_ticket_repository, fake_session
    ):
        fake_ticket_repository.add(ticket_anunciado())

        with pytest.raises(services.RecursoNaoEncontrado):
            services.confirmar_pedido(
                "p1", True, fake_pedido_repository, fake_ticket_repository, fake_session
            )

        assert fake_session.committed is False

    def test_ticket_inexistente_lanca_recurso_nao_encontrado(
        self, fake_pedido_repository, fake_ticket_repository, fake_session
    ):
        fake_pedido_repository.add(novo_pedido())

        with pytest.raises(services.RecursoNaoEncontrado):
            services.confirmar_pedido(
                "p1", True, fake_pedido_repository, fake_ticket_repository, fake_session
            )

        assert fake_session.committed is False

    def test_pedido_ja_confirmado_nao_pode_ser_confirmado_de_novo(
        self, fake_pedido_repository, fake_ticket_repository, fake_session
    ):
        fake_pedido_repository.add(novo_pedido())
        fake_ticket_repository.add(ticket_anunciado())
        services.confirmar_pedido(
            "p1", True, fake_pedido_repository, fake_ticket_repository, fake_session
        )

        with pytest.raises(model.PedidoEncerrado):
            services.confirmar_pedido(
                "p1", True, fake_pedido_repository, fake_ticket_repository, fake_session
            )

    def test_pedido_cancelado_nao_pode_ser_confirmado(
        self, fake_pedido_repository, fake_ticket_repository, fake_session
    ):
        pedido = novo_pedido()
        pedido.cancelar()
        fake_pedido_repository.add(pedido)
        fake_ticket_repository.add(ticket_anunciado())

        with pytest.raises(model.PedidoEncerrado):
            services.confirmar_pedido(
                "p1", True, fake_pedido_repository, fake_ticket_repository, fake_session
            )

        assert fake_session.committed is False


class TestCancelarPedido:
    def test_cancelar_encerra_o_pedido(self, fake_pedido_repository, fake_session):
        fake_pedido_repository.add(novo_pedido())

        services.cancelar_pedido("p1", fake_pedido_repository, fake_session)

        assert fake_pedido_repository.get("p1").status is StatusPedido.CANCELADO
        assert fake_session.committed is True

    def test_pedido_inexistente_lanca_recurso_nao_encontrado(
        self, fake_pedido_repository, fake_session
    ):
        with pytest.raises(services.RecursoNaoEncontrado):
            services.cancelar_pedido("p1", fake_pedido_repository, fake_session)

        assert fake_session.committed is False

    def test_pedido_ja_cancelado_nao_pode_ser_cancelado_de_novo(
        self, fake_pedido_repository, fake_session
    ):
        pedido = novo_pedido()
        pedido.cancelar()
        fake_pedido_repository.add(pedido)

        with pytest.raises(model.PedidoEncerrado):
            services.cancelar_pedido("p1", fake_pedido_repository, fake_session)

        assert fake_session.committed is False
