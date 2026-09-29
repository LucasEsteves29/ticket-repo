from rocketicket.service_layer import services


class TestTratamentoDeErros:
    def test_recurso_nao_encontrado_devolve_404(self, client):
        @client.application.get("/_teste/nao-encontrado")
        def nao_encontrado():
            raise services.RecursoNaoEncontrado("ticket t9 não existe")

        resposta = client.get("/_teste/nao-encontrado")

        assert resposta.status_code == 404
        assert resposta.get_json() == {"erro": "ticket t9 não existe"}
