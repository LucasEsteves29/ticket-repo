"""Modelo de domínio do RocketTicket.

Este módulo é puro: só usa a biblioteca padrão. NUNCA importar adapters,
service_layer, entrypoints, SQLAlchemy ou Flask aqui.

O arquivo é dividido em um bloco por agregado. Cada bloco guarda o enum de status, as
exceções e a raiz do próprio agregado.
"""

from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Iterable, Protocol


class ErroDeDominio(Exception):
    """Base de toda violação de invariante do domínio."""

class StatusTicket(Enum):
    DISPONIVEL = "disponivel"
    ANUNCIADO = "anunciado"
    VENDIDO = "vendido"
    USADO = "usado"


class TicketJaAnunciado(ErroDeDominio):
    """Tentativa de anunciar um ticket que já está em um anúncio ativo."""


class TicketJaUsado(ErroDeDominio):
    """Tentativa de anunciar ou vender um ticket que já foi usado."""


class TicketNaoAnunciado(ErroDeDominio):
    """Tentativa de vender um ticket que não está anunciado."""


class TicketNaoVendido(ErroDeDominio):
    """Tentativa de usar um ticket que ainda não foi vendido."""


class TicketAnunciado(ErroDeDominio):
    """Tentativa de usar um ticket que está em um anúncio ativo."""


class CompraDoProprioTicket(ErroDeDominio):
    """Tentativa de vender um ticket para quem já é o dono dele."""


class EstadoTicket:
    """Padrão State: o que cada método do Ticket faz em um dado status.

    Cada método aqui é o comportamento padrão, e cada subclasse sobrescreve só o
    que muda no seu status. Os estados não guardam nada: recebem o ticket, e a
    mesma instância serve para todos os tickets (ver _ESTADOS).
    """

    def anunciar(self, ticket: "Ticket") -> None:
        ticket.status = StatusTicket.ANUNCIADO

    def retirar_anuncio(self, ticket: "Ticket") -> None:
        raise self._nao_anunciado(ticket)

    def vender(self, ticket: "Ticket", novo_dono_id: str) -> None:
        raise self._nao_anunciado(ticket)

    def usar(self, ticket: "Ticket") -> None:
        raise TicketNaoVendido(
            f"ticket {ticket.id} não foi vendido (status: {ticket.status.value})"
        )

    def _nao_anunciado(self, ticket: "Ticket") -> TicketNaoAnunciado:
        return TicketNaoAnunciado(
            f"ticket {ticket.id} não está anunciado (status: {ticket.status.value})"
        )


class Disponivel(EstadoTicket):
    """Status sem regra própria: vale o comportamento padrão de EstadoTicket."""


class Anunciado(EstadoTicket):
    def anunciar(self, ticket: "Ticket") -> None:
        raise TicketJaAnunciado(f"ticket {ticket.id} já está anunciado")

    def retirar_anuncio(self, ticket: "Ticket") -> None:
        ticket.status = StatusTicket.VENDIDO

    def vender(self, ticket: "Ticket", novo_dono_id: str) -> None:
        if novo_dono_id == ticket.dono_id:
            raise CompraDoProprioTicket(
                f"usuário {novo_dono_id} já é o dono do ticket {ticket.id}"
            )
        ticket.dono_id = novo_dono_id
        ticket.status = StatusTicket.VENDIDO

    def usar(self, ticket: "Ticket") -> None:
        raise TicketAnunciado(f"ticket {ticket.id} está anunciado e não pode ser usado")


class Vendido(EstadoTicket):
    def usar(self, ticket: "Ticket") -> None:
        ticket.status = StatusTicket.USADO


class Usado(EstadoTicket):
    """Estado final: toda operação é recusada."""

    def anunciar(self, ticket: "Ticket") -> None:
        raise TicketJaUsado(f"ticket {ticket.id} já foi usado e não pode ser anunciado")

    def retirar_anuncio(self, ticket: "Ticket") -> None:
        raise TicketJaUsado(
            f"ticket {ticket.id} já foi usado e não pode ter o anúncio retirado."
        )

    def vender(self, ticket: "Ticket", novo_dono_id: str) -> None:
        raise TicketJaUsado(f"ticket {ticket.id} já foi usado e não pode ser vendido")

    def usar(self, ticket: "Ticket") -> None:
        raise TicketJaUsado(f"ticket {ticket.id} já foi usado")


# status é a única fonte de verdade: é a coluna persistida, e a leitura do banco
# não chama __init__. Um objeto de estado guardado na instância não existiria nos
# tickets carregados, por isso o estado é sempre obtido a partir do status.
_ESTADOS: dict[StatusTicket, EstadoTicket] = {
    StatusTicket.DISPONIVEL: Disponivel(),
    StatusTicket.ANUNCIADO: Anunciado(),
    StatusTicket.VENDIDO: Vendido(),
    StatusTicket.USADO: Usado(),
}


class Ticket:
    """Raiz do agregado Ticket.

    Ciclo de vida: VENDIDO <-> ANUNCIADO, e a qualquer momento VENDIDO -> USADO.

    O ticket nasce VENDIDO porque a emissão já é uma venda: a do organizador
    para o primeiro dono. Sem isso, quem compra do organizador e nunca revende
    ficaria preso em um estado que não satisfaz "só pode usar se foi vendido"
    e nunca conseguiria fazer check-in.

    Dali em diante ele alterna entre ANUNCIADO e VENDIDO a cada revenda, até
    ser USADO — estado final, que bloqueia anunciar e vender.

    O que cada método faz em cada status está nas subclasses de EstadoTicket.
    """

    def __init__(
        self,
        id: str,
        evento_id: str,
        valor_original: Decimal,
        dono_id: str,
    ):
        self.id = id
        self.evento_id = evento_id
        self.valor_original = valor_original
        self.dono_id = dono_id
        self.status = StatusTicket.VENDIDO

    @property
    def _estado(self) -> EstadoTicket:
        return _ESTADOS[self.status]

    def anunciar(self) -> None:
        """Coloca o ticket em um anúncio ativo.

        A regra "um ticket não pode estar em mais de um anúncio ativo" vive
        no agregado Ticket, e não na Venda, porque a raiz Venda só enxerga a si
        mesma.
        """
        self._estado.anunciar(self)

    def vender(self, novo_dono_id: str) -> None:
        """Conclui a venda do ticket, transferindo a posse ao comprador.

        O comprador não pode ser o dono atual: uma venda para si mesmo não
        muda nada de fato, mas queimaria o anúncio e a venda como se fosse
        uma transação real.
        """
        self._estado.vender(self, novo_dono_id)

    def usar(self) -> None:
        """Faz o check-in do ticket, seu estado final.

        Só pode ser usado se já foi vendido (não basta estar ANUNCIADO); uma
        vez usado, não pode ser usado de novo nem revendido/anunciado — ver
        anunciar() e vender().
        """
        self._estado.usar(self)

    def retirar_anuncio(self) -> None:
        """Retira o ticket de um anúncio ativo, revertendo para VENDIDO.

        É o inverso de anunciar(): o dono desiste de revender sem que uma
        venda tenha ocorrido, então não há transferência de posse aqui.
        """
        self._estado.retirar_anuncio(self)

    def __repr__(self) -> str:
        return f"<Ticket {self.id} {self.status.value}>"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Ticket):
            return False
        return other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)


class StatusVenda(Enum):
    ATIVA = "ativa"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"
class PrecoAcimaDoLimite(ErroDeDominio):
    """Tentativa de criar anúncio ou alterar preço acima de 110% do valor original."""
class VendaEncerrada(ErroDeDominio):
    """Tentativa de alterar, cancelar ou concluir uma venda já cancelada ou concluída."""
class ObservadorVenda:
    """Padrão Observer (Observer): quem quer ser avisado quando uma Venda termina.

    A Venda só conhece esta interface, nunca quem está do outro lado (e-mail,
    push, log). As implementações concretas ficam fora do domínio, em
    adapters/notifications.py.
    """
    def venda_concluida(self, venda: "Venda", comprador_id: str | None) -> None:
        raise NotImplementedError
    def venda_cancelada(self, venda: "Venda") -> None:
        raise NotImplementedError
class MementoDeOutraVenda(ErroDeDominio):
    """Tentativa de restaurar o preço de uma venda com o memento de outra venda."""
class MementoPrecoVenda:
    """Padrão Memento: o preço de uma Venda em um momento, guardado fora dela.

    Interface estreita (pública): só venda_id, para quem guarda o memento saber de
    qual anúncio ele é. Interface larga: _preco, lido só por Venda.restaurar_preco().
    Python não tem o friend do C++, então a fronteira é a convenção do sublinhado.
    O memento é passivo: só a Venda que o criou atribui ou lê o preço.
    """
    def __init__(self, venda_id: str, preco: Decimal):
        self._venda_id = venda_id
        self._preco = preco
    @property
    def venda_id(self) -> str:
        return self._venda_id
    def __repr__(self) -> str:
        return f"<MementoPrecoVenda da venda {self._venda_id}>"
class PoliticaTetoPercentual:
    """Responsável pelo cálculo e validação do teto de preço de revenda.
    Separa a regra financeira anti-cambismo (fator percentual e truncamento em
    centavos com ROUND_DOWN) do ciclo de vida da entidade Venda.
    """
    FATOR_PADRAO = Decimal("1.10")
    CENTAVO = Decimal("0.01")
    def __init__(self, fator_limite: Decimal = FATOR_PADRAO):
        self.fator_limite = fator_limite
    def calcular_limite(self, valor_original: Decimal) -> Decimal:
        """Calcula o preço máximo permitido, truncado para baixo em centavos."""
        return (valor_original * self.fator_limite).quantize(self.CENTAVO, rounding=ROUND_DOWN)
    def validar(self, preco: Decimal, valor_original: Decimal) -> None:
        """Recusa preço acima do limite calculado para o valor original."""
        limite_maximo = self.calcular_limite(valor_original)
        if preco > limite_maximo:
            percentual = int(self.fator_limite * 100)
            raise PrecoAcimaDoLimite(
                f"Preço {preco} excede o limite máximo permitido de {percentual}% ({limite_maximo})"
            )
class Venda:
    """Raiz do agregado Venda: o anúncio de revenda de um ticket.
    Nasce ATIVA e termina em CANCELADA (o vendedor desistiu) ou CONCLUIDA (o
    ticket foi vendido). Os dois estados finais não voltam a ATIVA nem aceitam
    novo preço. A validação do teto de revenda é delegada a PoliticaTetoPercentual.
    """
    politica_preco: PoliticaTetoPercentual = PoliticaTetoPercentual()
    def __init__(
        self,
        id: str,
        ticket_id: str,
        vendedor_id: str,
        preco: Decimal,
        valor_original: Decimal,
        politica_preco: PoliticaTetoPercentual | None = None,
    ):
        self.id = id
        self.ticket_id = ticket_id
        self.vendedor_id = vendedor_id
        self.valor_original = valor_original
        if politica_preco is not None:
            self.politica_preco = politica_preco
        self._validar_preco(preco)
        self.preco = preco
        self.status = StatusVenda.ATIVA
    def _validar_preco(self, preco: Decimal) -> None:
        """Delega a verificação do teto para a política de preço da venda."""
        self.politica_preco.validar(preco, self.valor_original)
    def alterar_preco(self, novo_preco: Decimal) -> None:
        """Troca o preço do anúncio, respeitando a política de limite da venda."""
        self._exigir_ativa("ter o preço alterado")
        self._validar_preco(novo_preco)
        self.preco = novo_preco
    def salvar_preco(self) -> MementoPrecoVenda:
        """Memento (CreateMemento): fotografa o preço atual do anúncio."""
        return MementoPrecoVenda(self.id, self.preco)
    def restaurar_preco(self, memento: MementoPrecoVenda) -> None:
        """Memento (SetMemento): volta o preço ao que estava guardado no memento.

        Segue as mesmas regras de alterar_preco(): venda encerrada não muda de
        preço e o preço restaurado precisa respeitar a política de teto atual.
        """
        self._exigir_ativa("ter o preço restaurado")
        if memento.venda_id != self.id:
            raise MementoDeOutraVenda(
                f"o preço guardado é da venda {memento.venda_id}, não da venda {self.id}"
            )
        self._validar_preco(memento._preco)
        self.preco = memento._preco
    def registrar_observador(self, observador: ObservadorVenda) -> None:
        """Observer (Attach): passa a avisar esse observador quando a venda terminar."""
        observadores = self._observadores()
        if observador not in observadores:
            observadores.append(observador)
    def remover_observador(self, observador: ObservadorVenda) -> None:
        """Observer (Detach): para de avisar esse observador."""
        observadores = self._observadores()
        if observador in observadores:
            observadores.remove(observador)
    def _observadores(self) -> list[ObservadorVenda]:
        """Lista de observadores, criada sob demanda.

        Fica fora do __init__ porque o SQLAlchemy recria a Venda carregada do banco
        sem chamar o __init__, e os observadores não são persistidos.
        """
        return self.__dict__.setdefault("_lista_observadores", [])
    def cancelar(self) -> None:
        """Encerra o anúncio sem venda. CANCELADA é estado final.

        Observer (Notify): depois de mudar o estado, avisa cada observador.
        """
        self._exigir_ativa("ser cancelada")
        self.status = StatusVenda.CANCELADA
        for observador in list(self._observadores()):
            observador.venda_cancelada(self)
    def concluir(self, comprador_id: str | None = None) -> None:
        """Encerra o anúncio com a venda feita. CONCLUIDA é estado final.

        Observer (Notify): depois de mudar o estado, avisa cada observador.
        """
        self._exigir_ativa("ser concluída")
        self.status = StatusVenda.CONCLUIDA
        for observador in list(self._observadores()):
            observador.venda_concluida(self, comprador_id)
    def _exigir_ativa(self, acao: str) -> None:
        """Venda cancelada ou concluída não volta a ATIVA nem muda de preço."""
        if self.status is not StatusVenda.ATIVA:
            raise VendaEncerrada(
                f"venda {self.id} está {self.status.value} e não pode {acao}"
            )
    def __repr__(self) -> str:
        return f"<Venda {self.id} {self.status.value}>"
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Venda):
            return False
        return self.id == other.id
    def __hash__(self) -> int:
        return hash(self.id)


class StatusPagamento(Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    RECUSADO = "recusado"


class StatusPedido(Enum):
    ABERTO = "aberto"
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"


class PagamentoJaProcessado(ErroDeDominio):
    """Tentativa de aprovar ou recusar um pagamento que já saiu de PENDENTE."""


class PagamentoNaoAprovado(ErroDeDominio):
    """Tentativa de confirmar um pedido cujo pagamento não foi aprovado."""


class TicketIndisponivel(ErroDeDominio):
    """Tentativa de confirmar um pedido cujo ticket não está à venda."""


class PedidoEncerrado(ErroDeDominio):
    """Tentativa de mexer em um pedido já confirmado ou cancelado."""


class RegraDeConfirmacao(Protocol):
    """Contrato para uma regra aplicada antes de confirmar um Pedido."""

    def validar(self, pedido: "Pedido", status_ticket: StatusTicket) -> None:
        ...


class PagamentoAprovadoParaConfirmacao:
    """Exige que o pagamento esteja aprovado antes da confirmação."""

    def validar(self, pedido: "Pedido", status_ticket: StatusTicket) -> None:
        if pedido.pagamento.status is not StatusPagamento.APROVADO:
            raise PagamentoNaoAprovado(
                f"pedido {pedido.id} tem pagamento {pedido.pagamento.status.value}"
            )


class TicketAnunciadoParaConfirmacao:
    """Exige que o ticket esteja anunciado antes da confirmação."""

    def validar(self, pedido: "Pedido", status_ticket: StatusTicket) -> None:
        if status_ticket is not StatusTicket.ANUNCIADO:
            raise TicketIndisponivel(
                f"ticket {pedido.ticket_id} não está à venda "
                f"(status: {status_ticket.value})"
            )


REGRAS_DE_CONFIRMACAO_PADRAO = (
    PagamentoAprovadoParaConfirmacao(),
    TicketAnunciadoParaConfirmacao(),
)


class Pagamento:
    """O pagamento do pedido. Mora dentro do Pedido, nao sai de la sozinho.

    Sai de PENDENTE uma única vez, para APROVADO ou RECUSADO. Quem garante
    que o pedido ainda está aberto é a raiz Pedido, não o Pagamento.
    """

    def __init__(self, valor: Decimal):
        self.valor = valor
        self.status = StatusPagamento.PENDENTE

    def aprovar(self) -> None:
        self._exigir_pendente("aprovado")
        self.status = StatusPagamento.APROVADO

    def recusar(self) -> None:
        self._exigir_pendente("recusado")
        self.status = StatusPagamento.RECUSADO

    def _exigir_pendente(self, acao: str) -> None:
        if self.status is not StatusPagamento.PENDENTE:
            raise PagamentoJaProcessado(
                f"pagamento está {self.status.value} e não pode ser {acao}"
            )


class Pedido:
    """Raiz do agregado Pedido.

    Ciclo de vida: nasce ABERTO e vai para CONFIRMADO ou CANCELADO, ambos
    estados finais. Todo acesso ao Pagamento passa por aqui.
    """

    def __init__(
        self,
        id: str,
        ticket_id: str,
        comprador_id: str,
        valor: Decimal,
        regras_confirmacao: Iterable[RegraDeConfirmacao] = None,
    ):
        self.id = id
        self.ticket_id = ticket_id
        self.comprador_id = comprador_id
        self.pagamento = Pagamento(valor)
        self.status = StatusPedido.ABERTO
        self._regras_confirmacao = tuple(
            regras_confirmacao or REGRAS_DE_CONFIRMACAO_PADRAO
        )

    def aprovar_pagamento(self) -> None:
        self._exigir_aberto("ter o pagamento alterado")
        self.pagamento.aprovar()

    def recusar_pagamento(self) -> None:
        self._exigir_aberto("ter o pagamento alterado")
        self.pagamento.recusar()

    def confirmar(self, status_ticket: StatusTicket) -> None:
        """Confirma o pedido com o status do ticket no momento da confirmação.

        O Pedido não enxerga o agregado Ticket, então o service lê o ticket e
        passa o status. "Disponível para compra" é ANUNCIADO — DISPONIVEL é
        inalcançável e não serve para essa checagem.
        """
        self._exigir_aberto("ser confirmado")
        regras = getattr(self, "_regras_confirmacao", REGRAS_DE_CONFIRMACAO_PADRAO)
        for regra in regras:
            regra.validar(self, status_ticket)
        self.status = StatusPedido.CONFIRMADO

    def cancelar(self) -> None:
        self._exigir_aberto("ser cancelado")
        self.status = StatusPedido.CANCELADO

    def _exigir_aberto(self, acao: str) -> None:
        """Pedido confirmado ou cancelado não volta a ABERTO nem muda de pagamento."""
        if self.status is not StatusPedido.ABERTO:
            raise PedidoEncerrado(
                f"pedido {self.id} está {self.status.value} e não pode {acao}"
            )

    def __repr__(self) -> str:
        return f"<Pedido {self.id} {self.status.value}>"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Pedido):
            return False
        return other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)
