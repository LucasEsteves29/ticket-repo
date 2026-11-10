"""Testes e2e de alterar e desfazer o preço de um anúncio (padrão Memento)."""


def criar_anuncio(client, preco="110.00"):
    client.post(
        "/tickets",
        json={"id": "t1", "evento_id": "ev1", "valor_original": "100.00", "dono_id": "u1"},
    )
    client.post(
        "/anuncios",
        json={"id": "v1", "ticket_id": "t1", "vendedor_id": "u1", "preco": preco},
    )


class TestPrecoDoAnuncio:
    def test_alterar_preco_devolve_200_e_o_novo_preco(self, client):
        criar_anuncio(client)
        resposta = client.put("/anuncios/v1/preco", json={"preco": "105.00"})
        assert resposta.status_code == 200
        assert resposta.get_json() == {"id": "v1", "preco": "105.00"}

    def test_desfazer_volta_um_passo_por_vez(self, client):
        criar_anuncio(client, preco="110.00")
        client.put("/anuncios/v1/preco", json={"preco": "105.00"})
        client.put("/anuncios/v1/preco", json={"preco": "100.00"})

        primeira = client.post("/anuncios/v1/preco/desfazimento")
        segunda = client.post("/anuncios/v1/preco/desfazimento")

        assert primeira.status_code == 200
        assert primeira.get_json() == {"id": "v1", "preco": "105.00"}
        assert segunda.get_json() == {"id": "v1", "preco": "110.00"}

    def test_desfazer_sem_alteracao_devolve_409(self, client):
        criar_anuncio(client)
        resposta = client.post("/anuncios/v1/preco/desfazimento")
        assert resposta.status_code == 409
        assert "erro" in resposta.get_json()

    def test_preco_recusado_nao_deixa_nada_para_desfazer(self, client):
        criar_anuncio(client)
        recusada = client.put("/anuncios/v1/preco", json={"preco": "110.01"})
        resposta = client.post("/anuncios/v1/preco/desfazimento")
        assert recusada.status_code == 400
        assert resposta.status_code == 409

    def test_anuncio_inexistente_devolve_404(self, client):
        assert client.put("/anuncios/v9/preco", json={"preco": "90.00"}).status_code == 404
        assert client.post("/anuncios/v9/preco/desfazimento").status_code == 404

    def test_preco_invalido_devolve_400(self, client):
        criar_anuncio(client)
        resposta = client.put("/anuncios/v1/preco", json={"preco": 90.5})
        assert resposta.status_code == 400