"""Notificações: observadores concretos do domínio (padrão Observer).

O domínio define ObservadorVenda; aqui ficam as implementações que de fato
avisam pessoas. O envio real (e-mail, push) fica atrás de AbstractNotificacoes,
para que os testes usem NotificacoesEmMemoria.
"""

import abc

from rocketicket.domain import model


class AbstractNotificacoes(abc.ABC):
    """Canal de envio de mensagens para um usuário."""

    @abc.abstractmethod
    def enviar(self, destinatario_id: str, mensagem: str) -> None:
        raise NotImplementedError


class NotificacoesEmMemoria(AbstractNotificacoes):
    """Guarda as mensagens numa lista, em vez de enviar. Usado em testes."""

    def __init__(self):
        self.enviadas: list[tuple[str, str]] = []

    def enviar(self, destinatario_id: str, mensagem: str) -> None:
        self.enviadas.append((destinatario_id, mensagem))

    def para(self, destinatario_id: str) -> list[str]:
        return [m for d, m in self.enviadas if d == destinatario_id]


class NotificadorDeVenda(model.ObservadorVenda):
    """Observer concreto (ConcreteObserver): avisa vendedor e comprador."""

    def __init__(self, notificacoes: AbstractNotificacoes):
        self.notificacoes = notificacoes

    def venda_concluida(self, venda: model.Venda, comprador_id: str | None) -> None:
        self.notificacoes.enviar(
            venda.vendedor_id,
            f"Seu anúncio {venda.id} foi vendido por {venda.preco}.",
        )
        if comprador_id is not None:
            self.notificacoes.enviar(
                comprador_id,
                f"Compra concluída: o ticket {venda.ticket_id} agora é seu.",
            )

    def venda_cancelada(self, venda: model.Venda) -> None:
        self.notificacoes.enviar(
            venda.vendedor_id,
            f"Seu anúncio {venda.id} foi cancelado.",
        )
