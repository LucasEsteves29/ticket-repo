"""Gateway de pagamento externo simulado.

Faz o papel do SDK de um fornecedor de pagamentos: código de terceiros, com
contrato próprio, que o RocketTicket não pode alterar. Por isso ele fala a língua
do fornecedor (payload em dicionário, chaves em inglês, valor em centavos) e não
conhece nada do domínio. Quem traduz é o AdaptadorGatewayExterno, em pagamento.py.

A simulação segue a convenção dos ambientes de teste dos gateways reais: o
resultado depende do token do cartão enviado.
"""

import uuid

TOKEN_APROVADO = "tok_aprovado"
TOKEN_RECUSADO = "tok_recusado"
TOKEN_FALHA = "tok_falha"


class ClienteGatewayExterno:
    """Cliente do gateway externo (o Adaptee do padrão Adapter)."""

    def create_charge(self, payload: dict) -> dict:
        """Cria uma cobrança e devolve a resposta do fornecedor.

        payload: {"amount_cents": int, "currency": "BRL", "order_ref": str,
        "card_token": str}

        resposta: {"charge_id": str | None, "status": "approved" | "declined" |
        "error", "reason": str | None}
        """
        amount = payload.get("amount_cents")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            return self._resposta(None, "error", "invalid_amount")
        if payload.get("currency") != "BRL":
            return self._resposta(None, "error", "unsupported_currency")

        token = payload.get("card_token")
        if token == TOKEN_FALHA:
            return self._resposta(None, "error", "service_unavailable")
        charge_id = f"ch_{uuid.uuid4().hex[:12]}"
        if token == TOKEN_APROVADO:
            return self._resposta(charge_id, "approved", None)
        if token == TOKEN_RECUSADO:
            return self._resposta(charge_id, "declined", "insufficient_funds")
        return self._resposta(charge_id, "declined", "invalid_card_token")

    @staticmethod
    def _resposta(charge_id, status, reason) -> dict:
        return {"charge_id": charge_id, "status": status, "reason": reason}
