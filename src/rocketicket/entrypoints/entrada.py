"""Leitura e validação da entrada JSON da API.

Entrada inválida é recusada com abort(400). Quem transforma isso na resposta
{"erro": ...} é o tratamento central de erros, em erros.py.
"""

from decimal import Decimal, InvalidOperation

from flask import abort, request


def ler_json(campos):
    """Devolve o corpo da requisição, que precisa ser um objeto JSON com esses campos."""
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        abort(400, "o corpo precisa ser um objeto JSON")
    faltando = [campo for campo in campos if campo not in dados]
    if faltando:
        abort(400, f"campos obrigatórios: {', '.join(faltando)}")
    return dados


def ler_texto(dados, campo):
    """Devolve o campo, que precisa ser uma string não vazia."""
    if not isinstance(dados[campo], str) or not dados[campo]:
        abort(400, f"{campo} precisa ser um texto não vazio")
    return dados[campo]


def ler_booleano(dados, campo):
    """Devolve o campo, que precisa ser um booleano do JSON: "true" e 1 não servem."""
    if not isinstance(dados[campo], bool):
        abort(400, f"{campo} precisa ser true ou false")
    return dados[campo]


def ler_decimal(dados, campo):
    """Converte o campo para Decimal.

    Dinheiro chega como string, com no máximo 2 casas: número em JSON vira float
    no Python e traria erro de arredondamento para o teto de revenda.
    """
    try:
        valor = Decimal(dados[campo]) if isinstance(dados[campo], str) else None
    except InvalidOperation:
        valor = None
    if valor is None or not valor.is_finite() or valor.as_tuple().exponent < -2:
        abort(400, f"{campo} inválido")
    return valor
