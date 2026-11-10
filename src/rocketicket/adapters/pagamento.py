"""Porta de pagamento do Pedido e o Adapter para o gateway externo.

O service_layer depende só de GatewayDePagamento (o Target do padrão Adapter).
O AdaptadorGatewayExterno traduz essa interface para o contrato do
ClienteGatewayExterno (o Adaptee), que é de terceiros e não pode ser alterado.
Trocar de fornecedor é escrever outro adaptador, sem tocar no service.
"""

import abc
from decimal import Decimal

from rocketicket.adapters.gateway_simulado import ClienteGatewayExterno


class GatewayIndisponivel(Exception):
    """O gateway não deu uma resposta de aprovação ou recusa (erro ou resposta inválida)."""


class GatewayDePagamento(abc.ABC):
    """Contrato que o RocketTicket espera de qualquer meio de pagamento."""

    @abc.abstractmethod
    def cobrar(self, pedido_id: str, valor: Decimal, token_pagamento: str) -> bool:
        """Cobra o valor do pedido. True se aprovado, False se recusado.

        Lança GatewayIndisponivel quando não há resposta definitiva: nesse caso
        o pagamento não deve ser marcado nem como aprovado nem como recusado.
        """
        raise NotImplementedError


class AdaptadorGatewayExterno(GatewayDePagamento):
    """Adapter (de objeto): implementa GatewayDePagamento delegando ao cliente externo.

    Traduz a chamada (Decimal em reais -> centavos inteiros, nomes do domínio ->
    chaves do fornecedor) e a resposta (status em texto do fornecedor -> bool ou
    GatewayIndisponivel).
    """

    MOEDA = "BRL"
    _RESULTADOS = {"approved": True, "declined": False}

    def __init__(self, cliente: ClienteGatewayExterno):
        self.cliente = cliente

    def cobrar(self, pedido_id: str, valor: Decimal, token_pagamento: str) -> bool:
        resposta = self.cliente.create_charge({
            "amount_cents": self._em_centavos(valor),
            "currency": self.MOEDA,
            "order_ref": pedido_id,
            "card_token": token_pagamento,
        })
        status = resposta.get("status") if isinstance(resposta, dict) else None
        if status not in self._RESULTADOS:
            motivo = resposta.get("reason") if isinstance(resposta, dict) else None
            raise GatewayIndisponivel(
                f"gateway de pagamento não processou o pedido {pedido_id}"
                + (f" ({motivo})" if motivo else "")
            )
        return self._RESULTADOS[status]

    @staticmethod
    def _em_centavos(valor: Decimal) -> int:
        """Converte reais em centavos sem arredondar: fração de centavo é erro."""
        centavos = valor * 100
        if centavos != centavos.to_integral_value():
            raise ValueError(f"valor {valor} tem fração de centavo")
        return int(centavos)
