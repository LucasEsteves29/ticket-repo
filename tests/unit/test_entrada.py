"""Testes unitários da leitura e validação da entrada JSON (entrypoints/entrada.py).

Não sobem o app: nada de create_app, mapeamento ou banco. ler_texto, ler_booleano e
ler_decimal só recebem um dict. ler_json lê o request do Flask, então roda no contexto
de requisição de um Flask vazio.
"""

from decimal import Decimal

import pytest
from flask import Flask
from werkzeug.exceptions import BadRequest

from rocketicket.entrypoints.entrada import (
    ler_booleano,
    ler_decimal,
    ler_json,
    ler_texto,
)

JSON = "application/json"


@pytest.fixture
def requisicao():
    return Flask(__name__).test_request_context


class TestLerJson:
    def test_devolve_o_objeto_com_os_campos_exigidos(self, requisicao):
        with requisicao(json={"id": "t1", "dono_id": "u1"}):
            assert ler_json(("id", "dono_id")) == {"id": "t1", "dono_id": "u1"}

    def test_mantem_campos_que_nao_foram_exigidos(self, requisicao):
        with requisicao(json={"id": "t1", "extra": 1}):
            assert ler_json(("id",)) == {"id": "t1", "extra": 1}

    def test_confere_so_a_presenca_do_campo_nao_o_valor(self, requisicao):
        with requisicao(json={"id": None}):
            assert ler_json(("id",)) == {"id": None}

    @pytest.mark.parametrize("corpo", [[1, 2], "texto", 10, True])
    def test_json_que_nao_e_objeto_falha(self, requisicao, corpo):
        with requisicao(json=corpo), pytest.raises(BadRequest) as erro:
            ler_json(("id",))
        assert erro.value.description == "o corpo precisa ser um objeto JSON"

    @pytest.mark.parametrize(
        "corpo, tipo",
        [
            ("{quebrado", JSON),
            ("null", JSON),
            ('{"id": "t1"}', "text/plain"),
        ],
    )
    def test_corpo_que_nao_vira_objeto_falha(self, requisicao, corpo, tipo):
        with requisicao(data=corpo, content_type=tipo), pytest.raises(BadRequest) as erro:
            ler_json(("id",))
        assert erro.value.description == "o corpo precisa ser um objeto JSON"

    def test_requisicao_sem_corpo_falha(self, requisicao):
        with requisicao(), pytest.raises(BadRequest) as erro:
            ler_json(("id",))
        assert erro.value.description == "o corpo precisa ser um objeto JSON"

    def test_campos_faltando_sao_listados_na_mensagem(self, requisicao):
        with requisicao(json={"id": "t1"}), pytest.raises(BadRequest) as erro:
            ler_json(("id", "evento_id", "dono_id"))
        assert erro.value.description == "campos obrigatórios: evento_id, dono_id"


class TestLerTexto:
    def test_devolve_o_texto(self):
        assert ler_texto({"id": "t1"}, "id") == "t1"

    @pytest.mark.parametrize("valor", ["", 123, None, True, ["t1"]])
    def test_valor_que_nao_e_texto_nao_vazio_falha(self, valor):
        with pytest.raises(BadRequest) as erro:
            ler_texto({"id": valor}, "id")
        assert erro.value.description == "id precisa ser um texto não vazio"


class TestLerBooleano:
    @pytest.mark.parametrize("valor", [True, False])
    def test_devolve_o_booleano(self, valor):
        assert ler_booleano({"aprovado": valor}, "aprovado") is valor

    @pytest.mark.parametrize("valor", ["true", "false", 1, 0, None])
    def test_valor_que_nao_e_booleano_falha(self, valor):
        with pytest.raises(BadRequest) as erro:
            ler_booleano({"aprovado": valor}, "aprovado")
        assert erro.value.description == "aprovado precisa ser true ou false"


class TestLerDecimal:
    @pytest.mark.parametrize("texto", ["150.00", "150.5", "150", "0.01"])
    def test_converte_o_texto_sem_mudar_as_casas(self, texto):
        valor = ler_decimal({"preco": texto}, "preco")
        assert isinstance(valor, Decimal)
        assert str(valor) == texto

    @pytest.mark.parametrize(
        "valor",
        [
            "abc",
            "",
            "NaN",
            "sNaN",
            "Infinity",
            "-Infinity",
            "150.999",
            "1E-3",
            100.5,
            100,
            None,
            True,
        ],
    )
    def test_valor_invalido_falha(self, valor):
        with pytest.raises(BadRequest) as erro:
            ler_decimal({"preco": valor}, "preco")
        assert erro.value.description == "preco inválido"
