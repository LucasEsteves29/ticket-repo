"""Modelo de domínio do RocketTicket.

Este módulo é puro: só usa a biblioteca padrão. NUNCA importar adapters,
service_layer, entrypoints, SQLAlchemy ou Flask aqui.

O arquivo é dividido em um bloco por agregado. Cada bloco guarda o enum de status, as
exceções e a raiz do próprio agregado.
"""

from decimal import Decimal
from enum import Enum


class ErroDeDominio(Exception):
    """Base de toda violação de invariante do domínio."""


class StatusTicket(Enum):

    DISPONIVEL = "disponivel"
    ANUNCIADO = "anunciado"
    VENDIDO = "vendido"
    USADO = "usado"


class TicketJaAnunciado(ErroDeDominio):
    """Tentativa de anunciar um ticket que já está em um anúncio ativo."""


class TicketJaUsado(ErroDeDominio):
    """Tentativa de anunciar ou vender um ticket que já foi usado."""


class TicketNaoAnunciado(ErroDeDominio):
    """Tentativa de vender um ticket que não está anunciado."""


class TicketNaoVendido(ErroDeDominio):
    """Tentativa de usar um ticket que ainda não foi vendido."""


class CompraDoProprioTicket(ErroDeDominio):
    """Tentativa de vender um ticket para quem já é o dono dele."""


class Ticket:
    """Raiz do agregado Ticket.

    Ciclo de vida: VENDIDO <-> ANUNCIADO, e a qualquer momento VENDIDO -> USADO.

    O ticket nasce VENDIDO porque a emissão já é uma venda: a do organizador
    para o primeiro dono. Sem isso, quem compra do organizador e nunca revende
    ficaria preso em um estado que não satisfaz "só pode usar se foi vendido"
    e nunca conseguiria fazer check-in.

    Dali em diante ele alterna entre ANUNCIADO e VENDIDO a cada revenda, até
    ser USADO — estado final, que bloqueia anunciar e vender.
    """

    def __init__(
        self,
        id: str,
        evento_id: str,
        valor_original: Decimal,
        dono_id: str,
    ):
        self.id = id
        self.evento_id = evento_id
        self.valor_original = valor_original
        self.dono_id = dono_id
        self.status = StatusTicket.VENDIDO

    def anunciar(self) -> None:
        """Coloca o ticket em um anúncio ativo.

        A regra "um ticket não pode estar em mais de um anúncio ativo" vive
        aqui, e não na Venda, porque a raiz Venda só enxerga a si mesma.
        """
        if self.status is StatusTicket.USADO:
            raise TicketJaUsado(
                f"ticket {self.id} já foi usado e não pode ser anunciado"
            )
        if self.status is StatusTicket.ANUNCIADO:
            raise TicketJaAnunciado(f"ticket {self.id} já está anunciado")
        self.status = StatusTicket.ANUNCIADO

    def vender(self, novo_dono_id: str) -> None:
        """Conclui a venda do ticket, transferindo a posse ao comprador.

        O comprador não pode ser o dono atual: uma venda para si mesmo não
        muda nada de fato, mas queimaria o anúncio e a venda como se fosse
        uma transação real.
        """
        if self.status is StatusTicket.USADO:
            raise TicketJaUsado(f"ticket {self.id} já foi usado e não pode ser vendido")
        if self.status is not StatusTicket.ANUNCIADO:
            raise TicketNaoAnunciado(
                f"ticket {self.id} não está anunciado (status: {self.status.value})"
            )
        if novo_dono_id == self.dono_id:
            raise CompraDoProprioTicket(
                f"usuário {novo_dono_id} já é o dono do ticket {self.id}"
            )
        self.dono_id = novo_dono_id
        self.status = StatusTicket.VENDIDO

    def __repr__(self) -> str:
        return f"<Ticket {self.id} {self.status.value}>"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Ticket):
            return False
        return other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)
