"""Testes da segregação da consulta da venda ativa (ISP).

O criar_pedido depende só de ConsultaVendaAtiva. Estes testes garantem que ele
funciona com uma fonte só de leitura, que não tem add() nem get(), e que o
repositório completo da Venda continua cumprindo o mesmo contrato.
"""

from decimal import Decimal

import pytest

from conftest import FakeVendaRepository
from rocketicket.adapters.repository import (
    AbstractVendaRepository,
    ConsultaVendaAtiva,
)
from rocketicket.domain.model import StatusPedido, Venda
from rocketicket.service_layer import services

PRECO = Decimal("105.00")


def anuncio_ativo():
    return Venda(
        id="v1",
        ticket_id="t1",
        vendedor_id="u1",
        preco=PRECO,
        valor_original=Decimal("100.00"),
    )


class ConsultaSoLeitura(ConsultaVendaAtiva):
    """Fonte só de leitura, como um cache de anúncios: não sabe gravar vendas."""

    def __init__(self, vendas):
        self._vendas = {v.ticket_id: v for v in vendas}

    def get_ativa_por_ticket(self, ticket_id):
        return self._vendas.get(ticket_id)


class TestCriarPedidoComConsultaSoLeitura:
    def test_cria_o_pedido_com_o_preco_do_anuncio(
        self, fake_pedido_repository, fake_session
    ):
        consulta = ConsultaSoLeitura([anuncio_ativo()])

        services.criar_pedido(
            "p1", "t1", "u2", fake_pedido_repository, consulta, fake_session
        )

        pedido = fake_pedido_repository.get("p1")
        assert pedido.status is StatusPedido.ABERTO
        assert pedido.pagamento.valor == PRECO
        assert fake_session.committed is True

    def test_ticket_sem_anuncio_ativo_continua_falhando(
        self, fake_pedido_repository, fake_session
    ):
        consulta = ConsultaSoLeitura([])

        with pytest.raises(services.RecursoNaoEncontrado):
            services.criar_pedido(
                "p1", "t1", "u2", fake_pedido_repository, consulta, fake_session
            )

        assert fake_session.committed is False

    def test_a_consulta_nao_expoe_escrita(self):
        consulta = ConsultaSoLeitura([anuncio_ativo()])

        assert not hasattr(consulta, "add")
        assert not hasattr(consulta, "get")


class TestContratoDoRepositorioDaVenda:
    def test_repositorio_completo_tambem_e_uma_consulta(self):
        assert issubclass(AbstractVendaRepository, ConsultaVendaAtiva)
        assert isinstance(FakeVendaRepository(), ConsultaVendaAtiva)

    def test_repositorio_sem_a_consulta_nao_pode_ser_instanciado(self):
        class SemConsulta(AbstractVendaRepository):
            def add(self, venda):
                pass

            def get(self, id):
                return None

        with pytest.raises(TypeError):
            SemConsulta()

    def test_consulta_sem_o_metodo_nao_pode_ser_instanciada(self):
        class Vazia(ConsultaVendaAtiva):
            pass

        with pytest.raises(TypeError):
            Vazia()
