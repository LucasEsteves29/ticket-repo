from decimal import Decimal

import pytest


@pytest.fixture
def ticket_app(fake_ticket_repository):
    from sqlalchemy.orm import clear_mappers

    from rocketicket.entrypoints.flask_app import create_app

    class Session:
        """Ciclo de transação sem operações de persistência SQLAlchemy."""

        def __init__(self):
            self.commits = 0
            self.closed = False

        def commit(self):
            self.commits += 1

        def close(self):
            self.closed = True

    sessions = []
    repository_sessions = []

    def session_factory():
        session = Session()
        sessions.append(session)
        return session

    def repository_factory(session):
        repository_sessions.append(session)
        return fake_ticket_repository

    try:
        app = create_app(
            session_factory, ticket_repository_factory=repository_factory
        )
        app.testing = True
        yield app.test_client(), sessions, repository_sessions
    finally:
        clear_mappers()


def dados_ticket():
    return {
        "id": "t1",
        "evento_id": "ev1",
        "valor_original": "100.00",
        "dono_id": "u1",
    }


def test_emite_ticket_com_repositorio_injetado_sem_banco(
    ticket_app, fake_ticket_repository
):
    client, sessions, repository_sessions = ticket_app

    resposta = client.post("/tickets", json=dados_ticket())

    assert resposta.status_code == 201
    assert resposta.get_json() == {"id": "t1"}
    ticket = fake_ticket_repository.get("t1")
    assert ticket.evento_id == "ev1"
    assert ticket.valor_original == Decimal("100.00")
    assert ticket.dono_id == "u1"
    assert repository_sessions == sessions
    assert len(sessions) == 1
    assert sessions[0].commits == 1
    assert sessions[0].closed


def test_fluxo_de_compra_usa_fabrica_de_ticket_em_todas_as_rotas(in_memory_db):
    from flask import request
    from sqlalchemy.orm import clear_mappers, sessionmaker

    from rocketicket.adapters.repository import SqlAlchemyTicketRepository
    from rocketicket.entrypoints.flask_app import create_app

    caminhos = []

    def repository_factory(session):
        caminhos.append(request.path)
        return SqlAlchemyTicketRepository(session)

    try:
        app = create_app(
            sessionmaker(bind=in_memory_db),
            ticket_repository_factory=repository_factory,
        )
        app.testing = True
        client = app.test_client()

        assert client.post("/tickets", json=dados_ticket()).status_code == 201
        assert client.post("/anuncios", json={
            "id": "v1", "ticket_id": "t1", "vendedor_id": "u1", "preco": "105.00"
        }).status_code == 201
        assert client.post("/pedidos", json={
            "id": "p1", "ticket_id": "t1", "comprador_id": "u2"
        }).status_code == 201
        resposta = client.post(
            "/pedidos/p1/confirmacao", json={"pagamento_aprovado": True}
        )

        assert resposta.status_code == 200
        assert resposta.get_json() == {"id": "p1", "pagamento": "aprovado"}
        assert caminhos == ["/tickets", "/anuncios", "/pedidos/p1/confirmacao"]
    finally:
        clear_mappers()


def test_ticket_duplicado_com_fake_preserva_409_e_nao_confirma_transacao(ticket_app):
    client, sessions, repository_sessions = ticket_app
    client.post("/tickets", json=dados_ticket())

    resposta = client.post("/tickets", json=dados_ticket())

    assert resposta.status_code == 409
    assert resposta.get_json() == {"erro": "ticket t1 já existe"}
    assert len(sessions) == 2
    assert sessions[0] is not sessions[1]
    assert repository_sessions == sessions
    assert [session.commits for session in sessions] == [1, 0]
    assert all(session.closed for session in sessions)


def test_entrada_invalida_com_fake_preserva_400_sem_persistir(
    ticket_app, fake_ticket_repository
):
    client, sessions, repository_sessions = ticket_app
    dados = dados_ticket() | {"valor_original": "abc"}

    resposta = client.post("/tickets", json=dados)

    assert resposta.status_code == 400
    assert "erro" in resposta.get_json()
    assert fake_ticket_repository.get("t1") is None
    assert repository_sessions == []
    assert sessions[0].commits == 0
    assert sessions[0].closed
