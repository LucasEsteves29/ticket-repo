"""Testes unitários do agregado Venda."""

from decimal import Decimal
import pytest

from rocketicket.domain.model import (
    PrecoAcimaDoLimite,
    StatusVenda,
    Venda,
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