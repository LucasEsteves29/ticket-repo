"""Testes de integração do caretaker SqlAlchemyHistoricoDePrecos (SQLite em memória)."""

from decimal import Decimal

from rocketicket.adapters.repository import SqlAlchemyHistoricoDePrecos
from rocketicket.domain.model import Venda


def nova_venda(id="v1", preco=Decimal("100.00")):
    return Venda(
        id=id,
        ticket_id="t1",
        vendedor_id="u1",
        preco=preco,
        valor_original=Decimal("100.00"),
    )


def guardar(session, *mementos):
    historico = SqlAlchemyHistoricoDePrecos(session)
    for memento in mementos:
        historico.guardar(memento)
    session.commit()
    session.expunge_all()


class TestSqlAlchemyHistoricoDePrecos:
    def test_memento_salvo_volta_e_restaura_o_preco(self, session):
        guardar(session, nova_venda(preco=Decimal("100.00")).salvar_preco())

        memento = SqlAlchemyHistoricoDePrecos(session).ultimo("v1")
        venda = nova_venda(preco=Decimal("90.00"))
        venda.restaurar_preco(memento)

        assert memento.venda_id == "v1"
        assert venda.preco == Decimal("100.00")
        assert isinstance(venda.preco, Decimal)

    def test_ultimo_devolve_o_mais_recente(self, session):
        venda = nova_venda(preco=Decimal("100.00"))
        primeiro = venda.salvar_preco()
        venda.alterar_preco(Decimal("90.00"))
        segundo = venda.salvar_preco()
        guardar(session, primeiro, segundo)

        memento = SqlAlchemyHistoricoDePrecos(session).ultimo("v1")
        restaurada = nova_venda(preco=Decimal("80.00"))
        restaurada.restaurar_preco(memento)

        assert restaurada.preco == Decimal("90.00")

    def test_ultimo_ignora_mementos_de_outras_vendas(self, session):
        guardar(session, nova_venda(id="v2").salvar_preco())
        assert SqlAlchemyHistoricoDePrecos(session).ultimo("v1") is None

    def test_descartar_tira_o_memento_do_historico(self, session):
        venda = nova_venda(preco=Decimal("100.00"))
        primeiro = venda.salvar_preco()
        venda.alterar_preco(Decimal("90.00"))
        guardar(session, primeiro, venda.salvar_preco())
        historico = SqlAlchemyHistoricoDePrecos(session)

        historico.descartar(historico.ultimo("v1"))
        session.commit()
        session.expunge_all()

        restaurada = nova_venda(preco=Decimal("80.00"))
        restaurada.restaurar_preco(historico.ultimo("v1"))
        assert restaurada.preco == Decimal("100.00")

    def test_guardar_nao_faz_commit(self, session):
        SqlAlchemyHistoricoDePrecos(session).guardar(nova_venda().salvar_preco())
        session.rollback()
        assert SqlAlchemyHistoricoDePrecos(session).ultimo("v1") is None