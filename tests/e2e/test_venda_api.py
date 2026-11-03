import pytest
def dados_ticket(**campos):
    return {
        "id": "t1",
        "evento_id": "ev1",
        "valor_original": "100.00",
        "dono_id": "u1",
    } | campos
def dados_anuncio(**campos):
    return {
        "id": "v1",
        "ticket_id": "t1",
        "vendedor_id": "u1",
        "preco": "110.00",
    } | campos
class TestPostAnuncios:
    def test_criar_anuncio_devolve_201_e_o_id(self, client):
        client.post("/tickets", json=dados_ticket())
        resposta = client.post("/anuncios", json=dados_anuncio())
        assert resposta.status_code == 201
        assert resposta.get_json() == {"id": "v1"}
    def test_criar_anuncio_id_repetido_devolve_409(self, client):
        client.post("/tickets", json=dados_ticket())
        client.post("/anuncios", json=dados_anuncio())
        resposta = client.post("/anuncios", json=dados_anuncio())
        assert resposta.status_code == 409
        assert "erro" in resposta.get_json()
    def test_criar_anuncio_ticket_inexistente_devolve_404(self, client):
        resposta = client.post("/anuncios", json=dados_anuncio(ticket_id="fantasma"))
        assert resposta.status_code == 404
        assert "erro" in resposta.get_json()
    def test_criar_anuncio_ticket_ja_anunciado_devolve_400(self, client):
        client.post("/tickets", json=dados_ticket())
        client.post("/anuncios", json=dados_anuncio(id="v1"))
        resposta = client.post("/anuncios", json=dados_anuncio(id="v2"))
        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()
    def test_preco_acima_do_limite_devolve_400(self, client):
        client.post("/tickets", json=dados_ticket())
        resposta = client.post("/anuncios", json=dados_anuncio(preco="110.01"))
        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()
    @pytest.mark.parametrize("campo", ["id", "ticket_id", "vendedor_id", "preco"])
    def test_campo_obrigatorio_faltando_devolve_400(self, client, campo):
        dados = dados_anuncio()
        del dados[campo]
        resposta = client.post("/anuncios", json=dados)
        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()
    @pytest.mark.parametrize("preco", ["abc", 150.5, "110.999", "NaN"])
    def test_preco_invalido_devolve_400(self, client, preco):
        dados = dados_anuncio(preco=preco)
        resposta = client.post("/anuncios", json=dados)
        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()