from decimal import Decimal, InvalidOperation

from flask import Flask, abort, g, request
from werkzeug.exceptions import HTTPException

from rocketicket.adapters import orm, repository
from rocketicket.domain import model
from rocketicket.service_layer import services

CAMPOS_TICKET = ("id", "evento_id", "valor_original", "dono_id")
CAMPOS_ANUNCIO = ("id", "ticket_id", "vendedor_id", "preco")

def create_app(session_factory):
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

    @app.errorhandler(model.ErroDeDominio)
    def erro_de_dominio(e):
        return {"erro": str(e)}, 400

    @app.errorhandler(services.ErroDeServico)
    def erro_de_servico(e):
        return {"erro": str(e)}, 409

    @app.errorhandler(services.RecursoNaoEncontrado)
    def recurso_nao_encontrado(e):
        return {"erro": str(e)}, 404

    @app.errorhandler(HTTPException)
    def erro_http(e):
        return {"erro": e.description}, e.code

    @app.post("/tickets")
    def emitir_ticket():
        dados = _ler_json(CAMPOS_TICKET)
        ticket_id = services.emitir_ticket(
            _ler_texto(dados, "id"),
            _ler_texto(dados, "evento_id"),
            _ler_decimal(dados, "valor_original"),
            _ler_texto(dados, "dono_id"),
            repository.SqlAlchemyTicketRepository(g.session),
            g.session,
        )
        return {"id": ticket_id}, 201

    # endpoints de Venda: Igor
    @app.post("/anuncios")
    def criar_anuncio():
        dados = _ler_json(CAMPOS_ANUNCIO)
        venda_id = services.criar_anuncio(
            _ler_texto(dados, "id"),
            _ler_texto(dados, "ticket_id"),
            _ler_texto(dados, "vendedor_id"),
            _ler_decimal(dados, "preco"),
            repository.SqlAlchemyVendaRepository(g.session),
            g.session,
        )
        return {"id": venda_id}, 201

    # endpoints de Pedido: Guilherme

    return app


def _ler_json(campos):
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        abort(400, "o corpo precisa ser um objeto JSON")
    faltando = [campo for campo in campos if campo not in dados]
    if faltando:
        abort(400, f"campos obrigatórios: {', '.join(faltando)}")
    return dados


def _ler_texto(dados, campo):
    if not isinstance(dados[campo], str) or not dados[campo]:
        abort(400, f"{campo} precisa ser um texto não vazio")
    return dados[campo]


def _ler_decimal(dados, campo):
    try:
        valor = Decimal(dados[campo]) if isinstance(dados[campo], str) else None
    except InvalidOperation:
        valor = None
    if valor is None or not valor.is_finite() or valor.as_tuple().exponent < -2:
        abort(400, f"{campo} inválido")
    return valor
