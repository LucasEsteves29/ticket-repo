import pytest


def dados_ticket(**campos):
    return {
        "id": "t1",
        "evento_id": "ev1",
        "valor_original": "100.00",
        "dono_id": "u1",
    } | campos


class TestPostTickets:
    def test_emitir_devolve_201_e_o_id(self, client):
        resposta = client.post("/tickets", json=dados_ticket())

        assert resposta.status_code == 201
        assert resposta.get_json() == {"id": "t1"}

    def test_emitir_id_repetido_devolve_409(self, client):
        client.post("/tickets", json=dados_ticket())

        resposta = client.post("/tickets", json=dados_ticket())

        assert resposta.status_code == 409
        assert "erro" in resposta.get_json()

    @pytest.mark.parametrize("campo", ["id", "evento_id", "valor_original", "dono_id"])
    def test_campo_faltando_devolve_400(self, client, campo):
        dados = dados_ticket()
        del dados[campo]

        resposta = client.post("/tickets", json=dados)

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()

    @pytest.mark.parametrize("valor", ["abc", "NaN", 100.5, "150.999"])
    def test_valor_original_invalido_devolve_400(self, client, valor):
        resposta = client.post("/tickets", json=dados_ticket(valor_original=valor))

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()

    @pytest.mark.parametrize("valor", [123, ""])
    def test_id_que_nao_e_texto_devolve_400(self, client, valor):
        resposta = client.post("/tickets", json=dados_ticket(id=valor))

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()

class TestErrosCentrais:
    def test_recurso_nao_encontrado_devolve_404(self, client):
        from rocketicket.service_layer import services

        def rota_que_nao_acha():
            raise services.RecursoNaoEncontrado("ticket t9 não existe")

        client.application.add_url_rule("/_teste_404", view_func=rota_que_nao_acha)

        resposta = client.get("/_teste_404")

        assert resposta.status_code == 404
        assert resposta.get_json() == {"erro": "ticket t9 não existe"}