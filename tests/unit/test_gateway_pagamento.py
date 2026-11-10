"""Testes do padrão Adapter: AdaptadorGatewayExterno sobre o ClienteGatewayExterno.

Os testes da tradução usam um cliente espião, que grava o payload e devolve uma
resposta fixa no formato do fornecedor. Os testes de ponta a ponta do adaptador
usam o gateway simulado de verdade, com os tokens do ambiente de teste.
"""

from decimal import Decimal

import pytest

from rocketicket.adapters.gateway_simulado import (
    TOKEN_APROVADO,
    TOKEN_FALHA,
    TOKEN_RECUSADO,
    ClienteGatewayExterno,
)
from rocketicket.adapters.pagamento import (
    AdaptadorGatewayExterno,
    GatewayDePagamento,
    GatewayIndisponivel,
)


class ClienteEspiao(ClienteGatewayExterno):
    def __init__(self, resposta):
        self.resposta = resposta
        self.payloads = []

    def create_charge(self, payload):
        self.payloads.append(payload)
        return self.resposta


def resposta(status, reason=None):
    return {"charge_id": "ch_1", "status": status, "reason": reason}


class TestTraducaoDaChamada:
    def test_adaptador_cumpre_o_contrato_do_dominio(self):
        assert isinstance(
            AdaptadorGatewayExterno(ClienteGatewayExterno()), GatewayDePagamento
        )

    def test_monta_o_payload_do_fornecedor(self):
        cliente = ClienteEspiao(resposta("approved"))

        AdaptadorGatewayExterno(cliente).cobrar("p1", Decimal("105.00"), "tok_x")

        assert cliente.payloads == [{
            "amount_cents": 10500,
            "currency": "BRL",
            "order_ref": "p1",
            "card_token": "tok_x",
        }]

    @pytest.mark.parametrize(
        "valor, centavos",
        [
            (Decimal("0.01"), 1),
            (Decimal("110.5"), 11050),
            (Decimal("99.99"), 9999),
            (Decimal("1000"), 100000),
        ],
    )
    def test_converte_reais_em_centavos_inteiros(self, valor, centavos):
        cliente = ClienteEspiao(resposta("approved"))

        AdaptadorGatewayExterno(cliente).cobrar("p1", valor, "tok_x")

        assert cliente.payloads[0]["amount_cents"] == centavos
        assert type(cliente.payloads[0]["amount_cents"]) is int

    def test_fracao_de_centavo_e_recusada_antes_de_chamar_o_fornecedor(self):
        cliente = ClienteEspiao(resposta("approved"))

        with pytest.raises(ValueError):
            AdaptadorGatewayExterno(cliente).cobrar("p1", Decimal("10.005"), "tok_x")

        assert cliente.payloads == []


class TestTraducaoDaResposta:
    def test_approved_vira_true(self):
        adaptador = AdaptadorGatewayExterno(ClienteEspiao(resposta("approved")))

        assert adaptador.cobrar("p1", Decimal("10.00"), "tok_x") is True

    def test_declined_vira_false(self):
        adaptador = AdaptadorGatewayExterno(
            ClienteEspiao(resposta("declined", "insufficient_funds"))
        )

        assert adaptador.cobrar("p1", Decimal("10.00"), "tok_x") is False

    def test_error_vira_gateway_indisponivel_com_o_motivo(self):
        adaptador = AdaptadorGatewayExterno(
            ClienteEspiao(resposta("error", "service_unavailable"))
        )

        with pytest.raises(GatewayIndisponivel, match="service_unavailable"):
            adaptador.cobrar("p1", Decimal("10.00"), "tok_x")

    @pytest.mark.parametrize(
        "resposta_estranha",
        [{}, {"status": "pending"}, {"status": None}, None, "approved"],
    )
    def test_resposta_fora_do_contrato_vira_gateway_indisponivel(
        self, resposta_estranha
    ):
        adaptador = AdaptadorGatewayExterno(ClienteEspiao(resposta_estranha))

        with pytest.raises(GatewayIndisponivel):
            adaptador.cobrar("p1", Decimal("10.00"), "tok_x")


class TestComOGatewaySimulado:
    def adaptador(self):
        return AdaptadorGatewayExterno(ClienteGatewayExterno())

    def test_token_aprovado(self):
        assert self.adaptador().cobrar("p1", Decimal("105.00"), TOKEN_APROVADO) is True

    def test_token_recusado(self):
        assert self.adaptador().cobrar("p1", Decimal("105.00"), TOKEN_RECUSADO) is False

    def test_token_desconhecido_e_recusado(self):
        assert self.adaptador().cobrar("p1", Decimal("105.00"), "tok_inventado") is False

    def test_token_de_falha_vira_gateway_indisponivel(self):
        with pytest.raises(GatewayIndisponivel):
            self.adaptador().cobrar("p1", Decimal("105.00"), TOKEN_FALHA)

    def test_valor_zero_e_recusado_pelo_fornecedor_como_erro(self):
        with pytest.raises(GatewayIndisponivel, match="invalid_amount"):
            self.adaptador().cobrar("p1", Decimal("0.00"), TOKEN_APROVADO)
