"""Tradução das exceções em respostas HTTP, todas com o corpo {"erro": ...}.

O Flask escolhe o tratador da classe mais específica: RecursoNaoEncontrado dá 404,
e não o 409 da sua base ErroDeServico.
"""

from werkzeug.exceptions import HTTPException

from rocketicket.adapters.pagamento import GatewayIndisponivel
from rocketicket.domain import model
from rocketicket.service_layer import services


def registrar_tratamento_de_erros(app):
    @app.errorhandler(model.ErroDeDominio)
    def erro_de_dominio(e):
        return {"erro": str(e)}, 400

    @app.errorhandler(services.ErroDeServico)
    def erro_de_servico(e):
        return {"erro": str(e)}, 409

    @app.errorhandler(services.RecursoNaoEncontrado)
    def recurso_nao_encontrado(e):
        return {"erro": str(e)}, 404

    @app.errorhandler(GatewayIndisponivel)
    def gateway_indisponivel(e):
        return {"erro": str(e)}, 502

    @app.errorhandler(HTTPException)
    def erro_http(e):
        return {"erro": e.description}, e.code
