"""Testes do padrão Memento no preço do anúncio (Venda + histórico de preços)."""

from decimal import Decimal

import pytest

from rocketicket.domain.model import (
    MementoDeOutraVenda,
    PoliticaTetoPercentual,
    PrecoAcimaDoLimite,
    Venda,
    VendaEncerrada,
)
from rocketicket.service_layer import services
from conftest import FakeHistoricoDePrecos, FakeVendaRepository

VALOR_ORIGINAL = Decimal("100.00")


def nova_venda(id="v1", preco=Decimal("100.00")):
    return Venda(
        id=id,
        ticket_id="t1",
        vendedor_id="u1",
        preco=preco,
        valor_original=VALOR_ORIGINAL,
    )


class TestMementoNaVenda:
    """Originator (Venda) e Memento (MementoPrecoVenda), sem caretaker."""

    def test_restaurar_volta_ao_preco_salvo(self):
        venda = nova_venda(preco=Decimal("100.00"))
        memento = venda.salvar_preco()
        venda.alterar_preco(Decimal("90.00"))

        venda.restaurar_preco(memento)

        assert venda.preco == Decimal("100.00")

    def test_memento_e_uma_foto_que_nao_muda_com_a_venda(self):
        venda = nova_venda(preco=Decimal("100.00"))
        memento = venda.salvar_preco()
        venda.alterar_preco(Decimal("90.00"))
        venda.alterar_preco(Decimal("80.00"))

        venda.restaurar_preco(memento)

        assert venda.preco == Decimal("100.00")

    def test_memento_expoe_so_o_id_da_venda(self):
        memento = nova_venda(id="v7").salvar_preco()
        assert memento.venda_id == "v7"
        assert not hasattr(memento, "preco")

    def test_restaurar_venda_cancelada_falha_e_mantem_o_preco(self):
        venda = nova_venda(preco=Decimal("100.00"))
        memento = venda.salvar_preco()
        venda.alterar_preco(Decimal("90.00"))
        venda.cancelar()

        with pytest.raises(VendaEncerrada):
            venda.restaurar_preco(memento)
        assert venda.preco == Decimal("90.00")

    def test_restaurar_venda_concluida_falha_e_mantem_o_preco(self):
        venda = nova_venda(preco=Decimal("100.00"))
        memento = venda.salvar_preco()
        venda.alterar_preco(Decimal("90.00"))
        venda.concluir()

        with pytest.raises(VendaEncerrada):
            venda.restaurar_preco(memento)
        assert venda.preco == Decimal("90.00")

    def test_memento_de_outra_venda_e_recusado(self):
        memento_v2 = nova_venda(id="v2", preco=Decimal("50.00")).salvar_preco()
        venda = nova_venda(id="v1", preco=Decimal("100.00"))

        with pytest.raises(MementoDeOutraVenda):
            venda.restaurar_preco(memento_v2)
        assert venda.preco == Decimal("100.00")

    def test_preco_restaurado_respeita_a_politica_atual(self):
        venda = nova_venda(preco=Decimal("110.00"))
        memento = venda.salvar_preco()
        venda.alterar_preco(Decimal("100.00"))
        venda.politica_preco = PoliticaTetoPercentual(fator_limite=Decimal("1.00"))

        with pytest.raises(PrecoAcimaDoLimite):
            venda.restaurar_preco(memento)
        assert venda.preco == Decimal("100.00")


def cenario(*vendas):
    return FakeVendaRepository(list(vendas) or [nova_venda()]), FakeHistoricoDePrecos()


class TestAlterarPrecoGuardaMemento:
    def test_alterar_preco_troca_o_preco_e_faz_commit(self, fake_session):
        repo_vendas, historico = cenario()

        services.alterar_preco("v1", Decimal("90.00"), repo_vendas, historico, fake_session)

        assert repo_vendas.get("v1").preco == Decimal("90.00")
        assert historico.ultimo("v1") is not None
        assert fake_session.committed is True

    def test_preco_recusado_nao_guarda_memento(self, fake_session):
        repo_vendas, historico = cenario()

        with pytest.raises(PrecoAcimaDoLimite):
            services.alterar_preco(
                "v1", Decimal("110.01"), repo_vendas, historico, fake_session
            )

        assert historico.ultimo("v1") is None
        assert fake_session.committed is False

    def test_venda_inexistente_lanca_404(self, fake_session):
        repo_vendas, historico = cenario()
        with pytest.raises(services.RecursoNaoEncontrado):
            services.alterar_preco(
                "fantasma", Decimal("90.00"), repo_vendas, historico, fake_session
            )


class TestDesfazerAlteracaoDePreco:
    def test_desfazer_volta_ao_preco_anterior(self, fake_session):
        repo_vendas, historico = cenario()
        services.alterar_preco("v1", Decimal("90.00"), repo_vendas, historico, fake_session)

        preco = services.desfazer_alteracao_de_preco(
            "v1", repo_vendas, historico, fake_session
        )

        assert preco == Decimal("100.00")
        assert repo_vendas.get("v1").preco == Decimal("100.00")
        assert historico.ultimo("v1") is None

    def test_desfaz_varias_alteracoes_da_mais_nova_para_a_mais_antiga(self, fake_session):
        repo_vendas, historico = cenario()
        for preco in ("105.00", "95.00", "90.00"):
            services.alterar_preco("v1", Decimal(preco), repo_vendas, historico, fake_session)

        desfeitos = [
            services.desfazer_alteracao_de_preco("v1", repo_vendas, historico, fake_session)
            for _ in range(3)
        ]

        assert desfeitos == [Decimal("95.00"), Decimal("105.00"), Decimal("100.00")]

    def test_sem_alteracao_lanca_erro_de_servico(self, fake_session):
        repo_vendas, historico = cenario()
        with pytest.raises(services.SemAlteracaoDePreco):
            services.desfazer_alteracao_de_preco("v1", repo_vendas, historico, fake_session)
        assert fake_session.committed is False

    def test_historico_de_uma_venda_nao_afeta_outra(self, fake_session):
        repo_vendas, historico = cenario(nova_venda("v1"), nova_venda("v2"))
        services.alterar_preco("v2", Decimal("90.00"), repo_vendas, historico, fake_session)

        with pytest.raises(services.SemAlteracaoDePreco):
            services.desfazer_alteracao_de_preco("v1", repo_vendas, historico, fake_session)
        assert repo_vendas.get("v2").preco == Decimal("90.00")

    def test_venda_encerrada_nao_desfaz_e_mantem_o_memento(self, fake_session):
        repo_vendas, historico = cenario()
        services.alterar_preco("v1", Decimal("90.00"), repo_vendas, historico, fake_session)
        repo_vendas.get("v1").cancelar()
        fake_session.committed = False

        with pytest.raises(VendaEncerrada):
            services.desfazer_alteracao_de_preco("v1", repo_vendas, historico, fake_session)

        assert repo_vendas.get("v1").preco == Decimal("90.00")
        assert historico.ultimo("v1") is not None
        assert fake_session.committed is False

    def test_venda_inexistente_lanca_404(self, fake_session):
        repo_vendas, historico = cenario()
        with pytest.raises(services.RecursoNaoEncontrado):
            services.desfazer_alteracao_de_preco(
                "fantasma", repo_vendas, historico, fake_session
            )