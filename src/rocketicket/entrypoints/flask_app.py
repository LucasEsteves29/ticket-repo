from collections.abc import Callable
from typing import Any

from flask import Flask, g

from rocketicket.adapters import orm, repository
from rocketicket.adapters.audit import SqlAlchemyCheckInAudit
from rocketicket.entrypoints.entrada import (
    ler_booleano,
    ler_decimal,
    ler_json,
    ler_texto,
)
from rocketicket.entrypoints.erros import registrar_tratamento_de_erros
from rocketicket.service_layer import services

CAMPOS_TICKET = ("id", "evento_id", "valor_original", "dono_id")
CAMPOS_ANUNCIO = ("id", "ticket_id", "vendedor_id", "preco")
CAMPOS_PEDIDO = ("id", "ticket_id", "comprador_id")
CAMPOS_CONFIRMACAO = ("pagamento_aprovado",)

def create_app(
    session_factory,
    *,
    ticket_repository_factory: Callable[[Any], repository.AbstractTicketRepository] = (
        repository.SqlAlchemyTicketRepository
    ),
):
    """Compõe a aplicação e permite escolher a persistência de Ticket.

    A fábrica recebe a sessão da requisição; o chamador continua responsável
    por confirmar a transação, e o teardown fecha a sessão.
    """
    orm.start_mappers()
    app = Flask(__name__)

    @app.before_request
    def abrir_sessao():
        g.session = session_factory()

    @app.teardown_request
    def fechar_sessao(exc):
        session = g.pop("session", None)
        if session is not None:
            session.close()

    registrar_tratamento_de_erros(app)

    @app.post("/tickets")
    def emitir_ticket():
        dados = ler_json(CAMPOS_TICKET)
        ticket_id = services.emitir_ticket(
            ler_texto(dados, "id"),
            ler_texto(dados, "evento_id"),
            ler_decimal(dados, "valor_original"),
            ler_texto(dados, "dono_id"),
            ticket_repository_factory(g.session),
            g.session,
        )
        return {"id": ticket_id}, 201

    @app.post("/tickets/<ticket_id>/check-in")
    def usar_ticket(ticket_id):
        repo = repository.AuditedTicketRepository(
            ticket_repository_factory(g.session),
            SqlAlchemyCheckInAudit(g.session),
        )
        services.usar_ticket(ticket_id, repo, g.session)
        return {"id": ticket_id, "status": "usado"}, 200

    # endpoints de Venda: Igor
    @app.post("/anuncios")
    def criar_anuncio():
        dados = ler_json(CAMPOS_ANUNCIO)
        venda_id = services.criar_anuncio(
            ler_texto(dados, "id"),
            ler_texto(dados, "ticket_id"),
            ler_texto(dados, "vendedor_id"),
            ler_decimal(dados, "preco"),
            repository.SqlAlchemyVendaRepository(g.session),
            ticket_repository_factory(g.session),
            g.session,
        )
        return {"id": venda_id}, 201

    # endpoints de Pedido: Guilherme
    @app.post("/pedidos")
    def criar_pedido():
        dados = ler_json(CAMPOS_PEDIDO)
        pedido_id = services.criar_pedido(
            ler_texto(dados, "id"),
            ler_texto(dados, "ticket_id"),
            ler_texto(dados, "comprador_id"),
            repository.SqlAlchemyPedidoRepository(g.session),
            repository.SqlAlchemyVendaRepository(g.session),
            g.session,
        )
        return {"id": pedido_id}, 201

    @app.post("/pedidos/<pedido_id>/confirmacao")
    def confirmar_pedido(pedido_id):
        dados = ler_json(CAMPOS_CONFIRMACAO)
        aprovado = ler_booleano(dados, "pagamento_aprovado")
        services.confirmar_pedido(
            pedido_id,
            aprovado,
            repository.SqlAlchemyPedidoRepository(g.session),
            ticket_repository_factory(g.session),
            g.session,
        )
        return {"id": pedido_id, "pagamento": "aprovado" if aprovado else "recusado"}, 200

    @app.post("/pedidos/<pedido_id>/cancelamento")
    def cancelar_pedido(pedido_id):
        services.cancelar_pedido(
            pedido_id,
            repository.SqlAlchemyPedidoRepository(g.session),
            g.session,
        )
        return {"id": pedido_id}, 200

    return app
