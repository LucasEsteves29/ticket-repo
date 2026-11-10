"""Testes do padrão Observer na Venda.

A Venda (Subject) avisa os observadores registrados quando é concluída ou
cancelada. NotificadorDeVenda (ConcreteObserver) transforma o aviso em
mensagens para o vendedor e para o comprador.
"""

from decimal import Decimal

import pytest

from rocketicket.adapters.notifications import NotificacoesEmMemoria, NotificadorDeVenda
from rocketicket.domain.model import ObservadorVenda, StatusVenda, Venda, VendaEncerrada


def nova_venda():
    return Venda(
        id="v1",
        ticket_id="t1",
        vendedor_id="vendedor",
        preco=Decimal("105.00"),
        valor_original=Decimal("100.00"),
    )


class ObservadorEspiao(ObservadorVenda):
    """Observador de teste: só anota o que recebeu."""

    def __init__(self):
        self.eventos = []

    def venda_concluida(self, venda, comprador_id):
        self.eventos.append(("concluida", venda.id, venda.status, comprador_id))

    def venda_cancelada(self, venda):
        self.eventos.append(("cancelada", venda.id, venda.status))


class TestVendaComoSubject:
    def test_concluir_avisa_o_observador_com_o_comprador(self):
        venda, espiao = nova_venda(), ObservadorEspiao()
        venda.registrar_observador(espiao)

        venda.concluir(comprador_id="comprador")

        assert espiao.eventos == [("concluida", "v1", StatusVenda.CONCLUIDA, "comprador")]

    def test_cancelar_avisa_o_observador(self):
        venda, espiao = nova_venda(), ObservadorEspiao()
        venda.registrar_observador(espiao)

        venda.cancelar()

        assert espiao.eventos == [("cancelada", "v1", StatusVenda.CANCELADA)]

    def test_todos_os_observadores_sao_avisados(self):
        venda, a, b = nova_venda(), ObservadorEspiao(), ObservadorEspiao()
        venda.registrar_observador(a)
        venda.registrar_observador(b)

        venda.cancelar()

        assert len(a.eventos) == 1
        assert len(b.eventos) == 1

    def test_observador_registrado_duas_vezes_e_avisado_uma_vez(self):
        venda, espiao = nova_venda(), ObservadorEspiao()
        venda.registrar_observador(espiao)
        venda.registrar_observador(espiao)

        venda.cancelar()

        assert len(espiao.eventos) == 1

    def test_observador_removido_nao_e_mais_avisado(self):
        venda, espiao = nova_venda(), ObservadorEspiao()
        venda.registrar_observador(espiao)
        venda.remover_observador(espiao)

        venda.concluir()

        assert espiao.eventos == []

    def test_operacao_recusada_nao_avisa_ninguem(self):
        venda, espiao = nova_venda(), ObservadorEspiao()
        venda.cancelar()
        venda.registrar_observador(espiao)

        with pytest.raises(VendaEncerrada):
            venda.concluir(comprador_id="comprador")

        assert espiao.eventos == []

    def test_venda_sem_observadores_continua_funcionando(self):
        venda = nova_venda()

        venda.concluir()

        assert venda.status is StatusVenda.CONCLUIDA

    def test_venda_recriada_sem_init_aceita_observador(self):
        # o SQLAlchemy recria a Venda carregada do banco sem chamar o __init__
        venda = Venda.__new__(Venda)
        venda.__dict__.update(
            id="v1", ticket_id="t1", vendedor_id="vendedor",
            preco=Decimal("105.00"), valor_original=Decimal("100.00"),
            status=StatusVenda.ATIVA,
        )
        espiao = ObservadorEspiao()
        venda.registrar_observador(espiao)

        venda.cancelar()

        assert espiao.eventos == [("cancelada", "v1", StatusVenda.CANCELADA)]


class TestNotificadorDeVenda:
    def test_venda_concluida_avisa_vendedor_e_comprador(self):
        notificacoes = NotificacoesEmMemoria()
        venda = nova_venda()
        venda.registrar_observador(NotificadorDeVenda(notificacoes))

        venda.concluir(comprador_id="comprador")

        assert notificacoes.para("vendedor") == ["Seu anúncio v1 foi vendido por 105.00."]
        assert notificacoes.para("comprador") == [
            "Compra concluída: o ticket t1 agora é seu."
        ]

    def test_venda_cancelada_avisa_so_o_vendedor(self):
        notificacoes = NotificacoesEmMemoria()
        venda = nova_venda()
        venda.registrar_observador(NotificadorDeVenda(notificacoes))

        venda.cancelar()

        assert notificacoes.enviadas == [("vendedor", "Seu anúncio v1 foi cancelado.")]
