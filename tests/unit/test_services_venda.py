from decimal import Decimal

import pytest

from rocketicket.domain import model
from rocketicket.domain.model import StatusTicket, StatusVenda, Ticket

from rocketicket.service_layer import services
from tests.conftest import FakeTicketRepository, FakeVendaRepository


VALOR_TICKET = Decimal("100.00")
PRECO_VENDA = Decimal("110.00")
def novo_ticket(dono_id="u1"):
    return Ticket(id="t1", evento_id="ev1", valor_original=VALOR_TICKET, dono_id=dono_id)
class TestCriarAnuncio:
    def test_criar_anuncio_salva_venda_e_anuncia_ticket(self, fake_session):
        repo_tickets = FakeTicketRepository([novo_ticket()])
        repo_vendas = FakeVendaRepository()
        venda_id = services.criar_anuncio(
            "v1", "t1", "u1", PRECO_VENDA, repo_vendas, repo_tickets, fake_session
        )
        assert venda_id == "v1"
        venda = repo_vendas.get("v1")
        assert venda.ticket_id == "t1"
        assert venda.preco == PRECO_VENDA
        assert venda.status is StatusVenda.ATIVA
        ticket = repo_tickets.get("t1")
        assert ticket.status is StatusTicket.ANUNCIADO
        assert fake_session.committed is True
    def test_criar_anuncio_ticket_inexistente_lanca_404(self, fake_session):
        repo_tickets = FakeTicketRepository()
        repo_vendas = FakeVendaRepository()
        with pytest.raises(services.RecursoNaoEncontrado):
            services.criar_anuncio(
                "v1", "ticket_fantasma", "u1", PRECO_VENDA, repo_vendas, repo_tickets, fake_session
            )
        assert fake_session.committed is False
    def test_criar_anuncio_id_duplicado_falha(self, fake_session):
        ticket = novo_ticket()
        repo_tickets = FakeTicketRepository([ticket])
        repo_vendas = FakeVendaRepository()
        services.criar_anuncio(
            "v1", "t1", "u1", PRECO_VENDA, repo_vendas, repo_tickets, fake_session
        )
        with pytest.raises(services.VendaJaExiste):
            services.criar_anuncio(
                "v1", "t1", "u1", PRECO_VENDA, repo_vendas, repo_tickets, fake_session
            )
    def test_criar_anuncio_ticket_ja_anunciado_falha(self, fake_session):
        ticket = novo_ticket()
        ticket.anunciar()
        repo_tickets = FakeTicketRepository([ticket])
        repo_vendas = FakeVendaRepository()
        with pytest.raises(model.TicketJaAnunciado):
            services.criar_anuncio(
                "v2", "t1", "u1", PRECO_VENDA, repo_vendas, repo_tickets, fake_session
            )
        assert fake_session.committed is False
        assert repo_vendas.get("v2") is None
    def test_criar_anuncio_preco_acima_do_limite_falha(self, fake_session):
        ticket = novo_ticket()
        repo_tickets = FakeTicketRepository([ticket])
        repo_vendas = FakeVendaRepository()
        preco_invalido = Decimal("110.01")
        with pytest.raises(model.PrecoAcimaDoLimite):
            services.criar_anuncio(
                "v1", "t1", "u1", preco_invalido, repo_vendas, repo_tickets, fake_session
            )
        assert fake_session.committed is False
        assert repo_vendas.get("v1") is None