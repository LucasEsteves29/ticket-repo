"""Teste de caracterização do ciclo de vida do Ticket.

Fixa, para cada par (status, método), o que o Ticket faz: para qual status vai
ou qual exceção lança, com a mensagem exata. Foi escrito e rodado contra o código
anterior ao padrão State, para garantir que a refatoração preserva o comportamento.
"""

from dataclasses import dataclass
from decimal import Decimal

import pytest

from rocketicket.domain.model import (
    CompraDoProprioTicket,
    StatusTicket,
    Ticket,
    TicketAnunciado,
    TicketJaAnunciado,
    TicketJaUsado,
    TicketNaoAnunciado,
    TicketNaoVendido,
)

DONO = "u1"
COMPRADOR = "u2"


def vendido():
    """Ticket recém-emitido: a emissão já é uma venda."""
    return Ticket(
        id="t1", evento_id="ev1", valor_original=Decimal("100.00"), dono_id=DONO
    )


def anunciado():
    ticket = vendido()
    ticket.anunciar()
    return ticket


def usado():
    ticket = vendido()
    ticket.usar()
    return ticket


def disponivel():
    """Ticket em DISPONIVEL, status que nenhum caminho da API alcança.

    Atribui o status na mão, o que a suíte evita, só para fixar o comportamento
    atual desse status. Os outros estados vêm da API do domínio.
    """
    ticket = vendido()
    ticket.status = StatusTicket.DISPONIVEL
    return ticket


MONTAR = {
    StatusTicket.DISPONIVEL: disponivel,
    StatusTicket.ANUNCIADO: anunciado,
    StatusTicket.VENDIDO: vendido,
    StatusTicket.USADO: usado,
}


@dataclass(frozen=True)
class Transicao:
    status_final: StatusTicket
    dono_final: str = DONO


@dataclass(frozen=True)
class Recusa:
    excecao: type[Exception]
    mensagem: str


MATRIZ = {
    "anunciar": {
        StatusTicket.DISPONIVEL: Transicao(StatusTicket.ANUNCIADO),
        StatusTicket.ANUNCIADO: Recusa(
            TicketJaAnunciado, "ticket t1 já está anunciado"
        ),
        StatusTicket.VENDIDO: Transicao(StatusTicket.ANUNCIADO),
        StatusTicket.USADO: Recusa(
            TicketJaUsado, "ticket t1 já foi usado e não pode ser anunciado"
        ),
    },
    "retirar_anuncio": {
        StatusTicket.DISPONIVEL: Recusa(
            TicketNaoAnunciado, "ticket t1 não está anunciado (status: disponivel)"
        ),
        StatusTicket.ANUNCIADO: Transicao(StatusTicket.VENDIDO),
        StatusTicket.VENDIDO: Recusa(
            TicketNaoAnunciado, "ticket t1 não está anunciado (status: vendido)"
        ),
        StatusTicket.USADO: Recusa(
            TicketJaUsado, "ticket t1 já foi usado e não pode ter o anúncio retirado."
        ),
    },
    "vender": {
        StatusTicket.DISPONIVEL: Recusa(
            TicketNaoAnunciado, "ticket t1 não está anunciado (status: disponivel)"
        ),
        StatusTicket.ANUNCIADO: Transicao(StatusTicket.VENDIDO, dono_final=COMPRADOR),
        StatusTicket.VENDIDO: Recusa(
            TicketNaoAnunciado, "ticket t1 não está anunciado (status: vendido)"
        ),
        StatusTicket.USADO: Recusa(
            TicketJaUsado, "ticket t1 já foi usado e não pode ser vendido"
        ),
    },
    "usar": {
        StatusTicket.DISPONIVEL: Recusa(
            TicketNaoVendido, "ticket t1 não foi vendido (status: disponivel)"
        ),
        StatusTicket.ANUNCIADO: Recusa(
            TicketAnunciado, "ticket t1 está anunciado e não pode ser usado"
        ),
        StatusTicket.VENDIDO: Transicao(StatusTicket.USADO),
        StatusTicket.USADO: Recusa(TicketJaUsado, "ticket t1 já foi usado"),
    },
}


def casos(metodo):
    return [
        pytest.param(status, esperado, id=status.value)
        for status, esperado in MATRIZ[metodo].items()
    ]


def conferir(status_inicial, esperado, acao):
    ticket = MONTAR[status_inicial]()

    if isinstance(esperado, Recusa):
        with pytest.raises(esperado.excecao) as erro:
            acao(ticket)
        assert str(erro.value) == esperado.mensagem
        assert ticket.status is status_inicial
        assert ticket.dono_id == DONO
    else:
        acao(ticket)
        assert ticket.status is esperado.status_final
        assert ticket.dono_id == esperado.dono_final


class TestMatriz:
    def test_cobre_todos_os_status_em_cada_metodo(self):
        for estados in MATRIZ.values():
            assert set(estados) == set(StatusTicket)


class TestAnunciar:
    @pytest.mark.parametrize("status, esperado", casos("anunciar"))
    def test_matriz(self, status, esperado):
        conferir(status, esperado, lambda ticket: ticket.anunciar())


class TestRetirarAnuncio:
    @pytest.mark.parametrize("status, esperado", casos("retirar_anuncio"))
    def test_matriz(self, status, esperado):
        conferir(status, esperado, lambda ticket: ticket.retirar_anuncio())


class TestVender:
    @pytest.mark.parametrize("status, esperado", casos("vender"))
    def test_matriz(self, status, esperado):
        conferir(status, esperado, lambda ticket: ticket.vender(COMPRADOR))

    def test_vender_ao_proprio_dono_falha(self):
        ticket = anunciado()

        with pytest.raises(CompraDoProprioTicket) as erro:
            ticket.vender(DONO)

        assert str(erro.value) == "usuário u1 já é o dono do ticket t1"
        assert ticket.status is StatusTicket.ANUNCIADO
        assert ticket.dono_id == DONO

    @pytest.mark.parametrize(
        "status",
        [StatusTicket.DISPONIVEL, StatusTicket.VENDIDO, StatusTicket.USADO],
    )
    def test_status_tem_prioridade_sobre_a_regra_do_proprio_dono(self, status):
        conferir(status, MATRIZ["vender"][status], lambda ticket: ticket.vender(DONO))


class TestUsar:
    @pytest.mark.parametrize("status, esperado", casos("usar"))
    def test_matriz(self, status, esperado):
        conferir(status, esperado, lambda ticket: ticket.usar())
