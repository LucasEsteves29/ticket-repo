"""Testes de integração do SqlAlchemyVendaRepository contra SQLite em memória."""

from decimal import Decimal

from sqlalchemy import text

from rocketicket.adapters.repository import SqlAlchemyVendaRepository
from rocketicket.domain.model import StatusVenda, Venda

VALOR_ORIGINAL = Decimal("100.00")
PRECO = Decimal("105.50")


def nova_venda(id="v1", ticket_id="t1"):
    return Venda(
        id=id,
        ticket_id=ticket_id,
        vendedor_id="u1",
        preco=PRECO,
        valor_original=VALOR_ORIGINAL,
    )


def salvar(session, *vendas):
    repo = SqlAlchemyVendaRepository(session)
    for venda in vendas:
        repo.add(venda)
    session.commit()
    session.expunge_all()
    return repo


class TestAddEGet:
    def test_venda_salva_volta_campo_a_campo(self, session):
        repo = salvar(session, nova_venda())

        lida = repo.get("v1")

        assert lida is not None
        assert lida.id == "v1"
        assert lida.ticket_id == "t1"
        assert lida.vendedor_id == "u1"
        assert lida.preco == PRECO
        assert lida.valor_original == VALOR_ORIGINAL
        assert lida.status is StatusVenda.ATIVA

    def test_get_de_id_inexistente_devolve_none(self, session):
        repo = SqlAlchemyVendaRepository(session)

        assert repo.get("nao-existe") is None

    def test_add_nao_faz_commit(self, session):
        repo = SqlAlchemyVendaRepository(session)

        repo.add(nova_venda())
        session.rollback()

        assert session.execute(text("SELECT COUNT(*) FROM vendas")).scalar_one() == 0


class TestGetAtivaPorTicket:
    def test_devolve_a_venda_ativa_do_ticket(self, session):
        repo = salvar(session, nova_venda())

        ativa = repo.get_ativa_por_ticket("t1")

        assert ativa is not None
        assert ativa.id == "v1"

    def test_ticket_sem_venda_devolve_none(self, session):
        repo = SqlAlchemyVendaRepository(session)

        assert repo.get_ativa_por_ticket("t1") is None

    def test_venda_cancelada_nao_conta_como_ativa(self, session):
        venda = nova_venda()
        venda.cancelar()
        repo = salvar(session, venda)

        assert repo.get_ativa_por_ticket("t1") is None

    def test_venda_concluida_nao_conta_como_ativa(self, session):
        venda = nova_venda()
        venda.concluir()
        repo = salvar(session, venda)

        assert repo.get_ativa_por_ticket("t1") is None

    def test_nao_confunde_tickets_diferentes(self, session):
        repo = salvar(session, nova_venda(id="v1", ticket_id="t1"))

        assert repo.get_ativa_por_ticket("t2") is None

    def test_acha_a_ativa_entre_uma_antiga_cancelada_e_uma_nova(self, session):
        antiga = nova_venda(id="v1")
        antiga.cancelar()
        repo = salvar(session, antiga, nova_venda(id="v2"))

        ativa = repo.get_ativa_por_ticket("t1")

        assert ativa is not None
        assert ativa.id == "v2"
