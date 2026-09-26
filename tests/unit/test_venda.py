"""Testes unitários do agregado Venda."""

from decimal import Decimal
import pytest

from rocketicket.domain.model import (
    PrecoAcimaDoLimite,
    StatusVenda,
    Venda,
    VendaEncerrada,
)

VALOR_ORIGINAL = Decimal("100.00")


class TestCriacaoVenda:
    def test_criar_venda(self):
        """Valida que a venda nasce como ATIVA com os dados e valor corretos."""
        venda = Venda(
            id="v1",
            ticket_id="t1",
            vendedor_id="u1",
            preco=Decimal("100.00"),
            valor_original=VALOR_ORIGINAL,
        )

        assert venda.id == "v1"
        assert venda.ticket_id == "t1"
        assert venda.vendedor_id == "u1"
        assert venda.preco == Decimal("100.00")
        assert venda.valor_original == VALOR_ORIGINAL
        assert venda.status is StatusVenda.ATIVA


class TestLimitePrecoVenda:
    def test_permitir_preco_110(self):
        """Valida que a regra de teto máximo é inclusiva (<= 110%)."""
        # 100.00 * 1.10 = 110.00 (limite exato)
        venda = Venda(
            id="v2",
            ticket_id="t1",
            vendedor_id="u1",
            preco=Decimal("110.00"),
            valor_original=VALOR_ORIGINAL,
        )

        assert venda.preco == Decimal("110.00")
        assert venda.status is StatusVenda.ATIVA

    def test_lancar_excecao_para_preco_acima_de_110(self):
        """Valida que qualquer valor superior a 110% lança PrecoAcimaDoLimite."""
        # 100.00 * 1.10 = 110.00 -> 110.01 excede o limite
        with pytest.raises(PrecoAcimaDoLimite):
            Venda(
                id="v3",
                ticket_id="t1",
                vendedor_id="u1",
                preco=Decimal("110.01"),
                valor_original=VALOR_ORIGINAL,
            )

    def test_permitir_preco_com_teto_arredondado_para_baixo(self):
        """99.99 * 1.10 = 109.989 -> teto truncado para baixo é 109.98."""
        venda = Venda(
            id="v4",
            ticket_id="t1",
            vendedor_id="u1",
            preco=Decimal("109.98"),
            valor_original=Decimal("99.99"),
        )
        assert venda.preco == Decimal("109.98")
        assert venda.status is StatusVenda.ATIVA

    def test_recusar_preco_acima_do_teto_com_tres_casas_decimais(self):
        """99.99 * 1.10 = 109.989 -> 109.99 excede o teto truncado de 109.98."""
        with pytest.raises(PrecoAcimaDoLimite):
            Venda(
                id="v5",
                ticket_id="t1",
                vendedor_id="u1",
                preco=Decimal("109.99"),
                valor_original=Decimal("99.99"),
            )

    def test_recusar_preco_entre_o_teto_arredondado_e_o_exato(self):
        """109.985 fica entre o teto truncado (109.98) e o exato (109.989)."""
        with pytest.raises(PrecoAcimaDoLimite):
            Venda(
                id="v6",
                ticket_id="t1",
                vendedor_id="u1",
                preco=Decimal("109.985"),
                valor_original=Decimal("99.99"),
            )


def nova_venda(preco=Decimal("100.00"), valor_original=VALOR_ORIGINAL):
    """Anúncio ativo, recém-criado."""
    return Venda(
        id="v1",
        ticket_id="t1",
        vendedor_id="u1",
        preco=preco,
        valor_original=valor_original,
    )


def cancelada():
    venda = nova_venda()
    venda.cancelar()
    return venda


def concluida():
    venda = nova_venda()
    venda.concluir()
    return venda


class TestAlterarPreco:
    def test_alterar_preco_dentro_do_limite(self):
        venda = nova_venda()
        venda.alterar_preco(Decimal("110.00"))
        assert venda.preco == Decimal("110.00")

    def test_novo_preco_acima_de_110_falha(self):
        venda = nova_venda()
        with pytest.raises(PrecoAcimaDoLimite):
            venda.alterar_preco(Decimal("110.01"))

    def test_preco_recusado_mantem_o_anterior(self):
        venda = nova_venda(preco=Decimal("100.00"))
        with pytest.raises(PrecoAcimaDoLimite):
            venda.alterar_preco(Decimal("150.00"))
        assert venda.preco == Decimal("100.00")

    def test_alterar_preco_ate_o_teto_arredondado_para_baixo(self):
        """99.99 * 1.10 = 109.989 -> teto truncado para baixo é 109.98."""
        venda = nova_venda(valor_original=Decimal("99.99"))
        venda.alterar_preco(Decimal("109.98"))
        assert venda.preco == Decimal("109.98")

    def test_alterar_preco_acima_do_teto_arredondado_falha(self):
        """99.99 * 1.10 = 109.989 -> 109.99 excede o teto truncado de 109.98."""
        venda = nova_venda(preco=Decimal("100.00"), valor_original=Decimal("99.99"))
        with pytest.raises(PrecoAcimaDoLimite):
            venda.alterar_preco(Decimal("109.99"))
        assert venda.preco == Decimal("100.00")

    def test_alterar_preco_entre_o_teto_arredondado_e_o_exato_falha(self):
        """109.985 fica entre o teto truncado (109.98) e o exato (109.989)."""
        venda = nova_venda(preco=Decimal("100.00"), valor_original=Decimal("99.99"))
        with pytest.raises(PrecoAcimaDoLimite):
            venda.alterar_preco(Decimal("109.985"))
        assert venda.preco == Decimal("100.00")

    def test_alterar_preco_de_venda_cancelada_falha(self):
        venda = cancelada()
        with pytest.raises(VendaEncerrada):
            venda.alterar_preco(Decimal("90.00"))
        assert venda.preco == Decimal("100.00")

    def test_alterar_preco_de_venda_concluida_falha(self):
        venda = concluida()
        with pytest.raises(VendaEncerrada):
            venda.alterar_preco(Decimal("90.00"))
        assert venda.preco == Decimal("100.00")


class TestEncerramento:
    def test_cancelar_marca_cancelada(self):
        assert cancelada().status is StatusVenda.CANCELADA

    def test_concluir_marca_concluida(self):
        assert concluida().status is StatusVenda.CONCLUIDA

    def test_venda_cancelada_nao_pode_ser_cancelada_de_novo(self):
        venda = cancelada()
        with pytest.raises(VendaEncerrada):
            venda.cancelar()

    def test_venda_concluida_nao_pode_ser_concluida_de_novo(self):
        venda = concluida()
        with pytest.raises(VendaEncerrada):
            venda.concluir()


class TestReativar:
    """Venda encerrada não volta a ATIVA por nenhum caminho."""

    def test_venda_cancelada_nao_pode_ser_concluida(self):
        venda = cancelada()
        with pytest.raises(VendaEncerrada):
            venda.concluir()
        assert venda.status is StatusVenda.CANCELADA

    def test_venda_concluida_nao_pode_ser_cancelada(self):
        venda = concluida()
        with pytest.raises(VendaEncerrada):
            venda.cancelar()
        assert venda.status is StatusVenda.CONCLUIDA