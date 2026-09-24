"""Testes unitários do agregado Ticket.

Escopo deste arquivo hoje: emissão, anunciar() e vender().
usar() e retirar_anuncio() ficam para o Caio, nos blocos reservados no fim.

Cada bloco é uma classe, para que os dois editem o arquivo em paralelo sem
conflitar. Nenhum teste atribui ticket.status na mão: todos os estados são
alcançados pela API do domínio, para que os testes sobrevivam ao
encapsulamento do agregado na Semana 8.
"""

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
)

VALOR = Decimal("100.00")


def novo_ticket(dono_id="u1"):
    """Ticket recém-emitido, como sairá de emitir_ticket() na Semana 4."""
    return Ticket(id="t1", evento_id="ev1", valor_original=VALOR, dono_id=dono_id)


def anunciado(dono_id="u1"):
    """Ticket em anúncio ativo, pronto para ser vendido."""
    ticket = novo_ticket(dono_id)
    ticket.anunciar()
    return ticket


def usado(dono_id="u1"):
    """Ticket que já passou pelo check-in — estado final."""
    ticket = novo_ticket(dono_id)
    ticket.usar()
    return ticket


class TestEmissao:
    def test_ticket_nasce_vendido(self):
        assert novo_ticket().status is StatusTicket.VENDIDO

    def test_ticket_nasce_com_o_dono_e_o_valor_da_emissao(self):
        ticket = novo_ticket(dono_id="u7")
        assert ticket.dono_id == "u7"
        assert ticket.valor_original == VALOR


class TestAnunciar:
    def test_anunciar_coloca_ticket_em_anuncio(self):
        ticket = novo_ticket()
        ticket.anunciar()
        assert ticket.status is StatusTicket.ANUNCIADO

    def test_anunciar_nao_troca_o_dono(self):
        ticket = novo_ticket(dono_id="u1")
        ticket.anunciar()
        assert ticket.dono_id == "u1"

    def test_anunciar_ticket_ja_anunciado_falha(self):
        ticket = anunciado()
        with pytest.raises(TicketJaAnunciado):
            ticket.anunciar()

    def test_anunciar_ticket_usado_falha(self):
        ticket = usado()
        with pytest.raises(TicketJaUsado):
            ticket.anunciar()


class TestVender:
    def test_vender_transfere_posse_e_marca_vendido(self):
        ticket = anunciado(dono_id="u1")
        ticket.vender("u2")
        assert ticket.status is StatusTicket.VENDIDO
        assert ticket.dono_id == "u2"

    def test_vender_nao_altera_o_valor_original(self):
        ticket = anunciado()
        ticket.vender("u2")
        assert ticket.valor_original == VALOR

    def test_vender_sem_anuncio_falha(self):
        ticket = novo_ticket()
        with pytest.raises(TicketNaoAnunciado):
            ticket.vender("u2")

    def test_vender_ticket_usado_falha(self):
        ticket = usado()
        with pytest.raises(TicketJaUsado):
            ticket.vender("u2")

    def test_vender_para_o_proprio_dono_falha(self):
        ticket = anunciado(dono_id="u1")
        with pytest.raises(CompraDoProprioTicket):
            ticket.vender("u1")

    def test_vender_recusada_nao_altera_o_ticket(self):
        ticket = anunciado(dono_id="u1")
        with pytest.raises(CompraDoProprioTicket):
            ticket.vender("u1")
        assert ticket.status is StatusTicket.ANUNCIADO
        assert ticket.dono_id == "u1"

    def test_ticket_pode_ser_revendido_varias_vezes(self):
        ticket = novo_ticket(dono_id="u1")
        for comprador in ("u2", "u3", "u4"):
            ticket.anunciar()
            ticket.vender(comprador)
        assert ticket.status is StatusTicket.VENDIDO
        assert ticket.dono_id == "u4"

    def test_dono_anterior_pode_recomprar(self):
        
        ticket = anunciado(dono_id="u1")
        ticket.vender("u2")
        ticket.anunciar()
        ticket.vender("u1")
        assert ticket.dono_id == "u1"

class TestUsar:
    def test_usar_faz_o_checkin(self):
        ticket = novo_ticket()
        ticket.usar()
        assert ticket.status is StatusTicket.USADO

    def test_usar_ticket_ja_usado_falha(self):
        ticket = usado()
        with pytest.raises(TicketJaUsado):
            ticket.usar()

    def test_usar_ticket_anunciado_falha(self):
        ticket = anunciado()
        with pytest.raises(TicketAnunciado):
            ticket.usar()

    def test_usar_nao_troca_o_dono(self):
        ticket = novo_ticket(dono_id="u1")
        ticket.usar()
        assert ticket.dono_id == "u1"

    def test_usar_recusado_nao_altera_o_ticket(self):
        ticket = anunciado(dono_id="u1")
        with pytest.raises(TicketAnunciado):
            ticket.usar()
        assert ticket.status is StatusTicket.ANUNCIADO
        assert ticket.dono_id == "u1"

    def test_usar_depois_de_revenda_funciona(self):
        ticket = anunciado(dono_id="u1")
        ticket.vender("u2")
        ticket.usar()
        assert ticket.status is StatusTicket.USADO
        assert ticket.dono_id == "u2"


class TestRetirarAnuncio:
    def test_retirar_anuncio_volta_para_vendido(self):
        ticket = anunciado()
        ticket.retirar_anuncio()
        assert ticket.status is StatusTicket.VENDIDO

    def test_retirar_anuncio_nao_troca_o_dono(self):
        ticket = anunciado(dono_id="u1")
        ticket.retirar_anuncio()
        assert ticket.dono_id == "u1"

    def test_retirar_anuncio_sem_anuncio_ativo_falha(self):
        ticket = novo_ticket()
        with pytest.raises(TicketNaoAnunciado):
            ticket.retirar_anuncio()

    def test_retirar_anuncio_de_ticket_usado_falha(self):
        ticket = usado()
        with pytest.raises(TicketJaUsado):
            ticket.retirar_anuncio()

    def test_ticket_pode_ser_reanunciado_depois_de_retirado(self):
        ticket = anunciado()
        ticket.retirar_anuncio()
        ticket.anunciar()
        assert ticket.status is StatusTicket.ANUNCIADO        
