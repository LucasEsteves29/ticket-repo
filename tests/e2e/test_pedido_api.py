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
        "preco": "105.00",
    } | campos


def dados_pedido(**campos):
    return {
        "id": "p1",
        "ticket_id": "t1",
        "comprador_id": "u2",
    } | campos


@pytest.fixture
def ticket_anunciado(client):
    client.post("/tickets", json=dados_ticket())
    client.post("/anuncios", json=dados_anuncio())


@pytest.fixture
def pedido_aberto(client, ticket_anunciado):
    client.post("/pedidos", json=dados_pedido())


class TestPostPedidos:
    def test_criar_pedido_devolve_201_e_o_id(self, client, ticket_anunciado):
        resposta = client.post("/pedidos", json=dados_pedido())

        assert resposta.status_code == 201
        assert resposta.get_json() == {"id": "p1"}

    def test_criar_pedido_id_repetido_devolve_409(self, client, pedido_aberto):
        resposta = client.post("/pedidos", json=dados_pedido())

        assert resposta.status_code == 409
        assert "erro" in resposta.get_json()

    def test_ticket_sem_anuncio_devolve_404(self, client):
        client.post("/tickets", json=dados_ticket())

        resposta = client.post("/pedidos", json=dados_pedido())

        assert resposta.status_code == 404
        assert "erro" in resposta.get_json()

    def test_ticket_inexistente_devolve_404(self, client):
        resposta = client.post("/pedidos", json=dados_pedido(ticket_id="fantasma"))

        assert resposta.status_code == 404
        assert "erro" in resposta.get_json()

    @pytest.mark.parametrize("campo", ["id", "ticket_id", "comprador_id"])
    def test_campo_obrigatorio_faltando_devolve_400(self, client, campo):
        dados = dados_pedido()
        del dados[campo]

        resposta = client.post("/pedidos", json=dados)

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()

    @pytest.mark.parametrize("valor", ["", 123, None])
    def test_comprador_invalido_devolve_400(self, client, valor):
        resposta = client.post("/pedidos", json=dados_pedido(comprador_id=valor))

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()


class TestPostConfirmacaoPedido:
    def test_pagamento_aprovado_devolve_200(self, client, pedido_aberto):
        resposta = client.post(
            "/pedidos/p1/confirmacao", json={"pagamento_aprovado": True}
        )

        assert resposta.status_code == 200
        assert resposta.get_json() == {"id": "p1", "pagamento": "aprovado"}

    def test_pagamento_recusado_devolve_200_com_recusa(self, client, pedido_aberto):
        resposta = client.post(
            "/pedidos/p1/confirmacao", json={"pagamento_aprovado": False}
        )

        assert resposta.status_code == 200
        assert resposta.get_json() == {"id": "p1", "pagamento": "recusado"}

    def test_pagamento_recusado_nao_pode_ser_aprovado_depois(
        self, client, pedido_aberto
    ):
        client.post("/pedidos/p1/confirmacao", json={"pagamento_aprovado": False})

        resposta = client.post(
            "/pedidos/p1/confirmacao", json={"pagamento_aprovado": True}
        )

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()

    def test_pedido_ja_confirmado_devolve_400(self, client, pedido_aberto):
        client.post("/pedidos/p1/confirmacao", json={"pagamento_aprovado": True})

        resposta = client.post(
            "/pedidos/p1/confirmacao", json={"pagamento_aprovado": True}
        )

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()

    def test_pedido_cancelado_devolve_400(self, client, pedido_aberto):
        client.post("/pedidos/p1/cancelamento")

        resposta = client.post(
            "/pedidos/p1/confirmacao", json={"pagamento_aprovado": True}
        )

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()

    def test_pedido_inexistente_devolve_404(self, client):
        resposta = client.post(
            "/pedidos/fantasma/confirmacao", json={"pagamento_aprovado": True}
        )

        assert resposta.status_code == 404
        assert "erro" in resposta.get_json()

    def test_campo_faltando_devolve_400(self, client, pedido_aberto):
        resposta = client.post("/pedidos/p1/confirmacao", json={})

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()

    @pytest.mark.parametrize("valor", ["true", 1, None])
    def test_pagamento_aprovado_invalido_devolve_400(self, client, pedido_aberto, valor):
        resposta = client.post(
            "/pedidos/p1/confirmacao", json={"pagamento_aprovado": valor}
        )

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()


class TestPostCancelamentoPedido:
    def test_cancelar_pedido_devolve_200(self, client, pedido_aberto):
        resposta = client.post("/pedidos/p1/cancelamento")

        assert resposta.status_code == 200
        assert resposta.get_json() == {"id": "p1"}

    def test_cancelar_pedido_inexistente_devolve_404(self, client):
        resposta = client.post("/pedidos/fantasma/cancelamento")

        assert resposta.status_code == 404
        assert "erro" in resposta.get_json()

    def test_cancelar_pedido_ja_cancelado_devolve_400(self, client, pedido_aberto):
        client.post("/pedidos/p1/cancelamento")

        resposta = client.post("/pedidos/p1/cancelamento")

        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()
