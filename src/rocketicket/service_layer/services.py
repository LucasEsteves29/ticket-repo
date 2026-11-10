from decimal import Decimal

from rocketicket.adapters.pagamento import GatewayDePagamento
from rocketicket.adapters.repository import (
    AbstractHistoricoDePrecos,
    AbstractRepository,
    AbstractTicketRepository,
    ConsultaVendaAtiva,
)
from rocketicket.domain import model


class ErroDeServico(Exception):
    pass


class RecursoNaoEncontrado(ErroDeServico):
    pass


class TicketJaExiste(ErroDeServico):
    pass

class VendaJaExiste(ErroDeServico):
    pass


class PedidoJaExiste(ErroDeServico):
    pass

class SemAlteracaoDePreco(ErroDeServico):
    """Pedido para desfazer o preço de um anúncio sem alteração guardada."""

def emitir_ticket(
    id: str,
    evento_id: str,
    valor_original: Decimal,
    dono_id: str,
    repo: AbstractRepository[model.Ticket],
    session,
) -> str:
    if repo.get(id) is not None:
        raise TicketJaExiste(f"ticket {id} já existe")
    ticket = model.Ticket(
        id=id, evento_id=evento_id, valor_original=valor_original, dono_id=dono_id
    )
    repo.add(ticket)
    session.commit()
    return ticket.id


# usar_ticket: Caio
def usar_ticket(
    ticket_id: str,
    repo: AbstractTicketRepository,
    session,
) -> None:
    if repo.usar(ticket_id) is None:
        raise RecursoNaoEncontrado(f"ticket {ticket_id} não existe")
    session.commit()


# criar_anuncio: Igor

def criar_anuncio(
    id: str,
    ticket_id: str,
    vendedor_id: str,
    preco: Decimal,
    repo_vendas: AbstractRepository[model.Venda],
    repo_tickets: AbstractRepository[model.Ticket],
    session,
    politica_preco: model.PoliticaTetoPercentual | None = None,
) -> str:
    ticket = repo_tickets.get(ticket_id)
    if ticket is None:
        raise RecursoNaoEncontrado(f"ticket {ticket_id} não existe")
    if repo_vendas.get(id) is not None:
        raise VendaJaExiste(f"venda {id} já existe")
    ticket.anunciar()
    venda = model.Venda(
        id=id,
        ticket_id=ticket.id,
        vendedor_id=vendedor_id,
        preco=preco,
        valor_original=ticket.valor_original,
        politica_preco=politica_preco,
    )
    repo_vendas.add(venda)
    session.commit()
    return venda.id

# alterar_preco e desfazer_alteracao_de_preco (padrão Memento): Igor


def alterar_preco(
    venda_id: str,
    novo_preco: Decimal,
    repo_vendas: AbstractRepository[model.Venda],
    historico: AbstractHistoricoDePrecos,
    session,
) -> None:
    """Troca o preço do anúncio e guarda o preço anterior para poder desfazer.

    O memento é criado antes da troca e só é guardado se a troca passar: um
    preço recusado pelo domínio não deixa nada para desfazer.
    """
    venda = repo_vendas.get(venda_id)
    if venda is None:
        raise RecursoNaoEncontrado(f"venda {venda_id} não existe")
    memento = venda.salvar_preco()
    venda.alterar_preco(novo_preco)
    historico.guardar(memento)
    session.commit()


def desfazer_alteracao_de_preco(
    venda_id: str,
    repo_vendas: AbstractRepository[model.Venda],
    historico: AbstractHistoricoDePrecos,
    session,
) -> Decimal:
    """Volta o anúncio ao preço anterior à última alteração e devolve o preço.

    O memento só sai do histórico depois que a Venda aceita a restauração. Se
    ela recusar (venda encerrada, por exemplo), nada muda e nada é salvo.
    """
    venda = repo_vendas.get(venda_id)
    if venda is None:
        raise RecursoNaoEncontrado(f"venda {venda_id} não existe")
    memento = historico.ultimo(venda_id)
    if memento is None:
        raise SemAlteracaoDePreco(
            f"venda {venda_id} não tem alteração de preço para desfazer"
        )
    venda.restaurar_preco(memento)
    historico.descartar(memento)
    session.commit()
    return venda.preco


# alterar_preco e cancelar_anuncio: Miguel


# criar_pedido, confirmar_pedido e cancelar_pedido: Guilherme


def criar_pedido(
    id: str,
    ticket_id: str,
    comprador_id: str,
    repo_pedidos: AbstractRepository[model.Pedido],
    repo_vendas: ConsultaVendaAtiva,
    session,
) -> str:
    venda = repo_vendas.get_ativa_por_ticket(ticket_id)
    if venda is None:
        raise RecursoNaoEncontrado(f"ticket {ticket_id} não tem anúncio ativo")
    if repo_pedidos.get(id) is not None:
        raise PedidoJaExiste(f"pedido {id} já existe")
    pedido = model.Pedido(
        id=id, ticket_id=ticket_id, comprador_id=comprador_id, valor=venda.preco
    )
    repo_pedidos.add(pedido)
    session.commit()
    return pedido.id


def confirmar_pedido(
    pedido_id: str,
    token_pagamento: str,
    repo_pedidos: AbstractRepository[model.Pedido],
    repo_tickets: AbstractRepository[model.Ticket],
    gateway: GatewayDePagamento,
    session,
) -> bool:
    """Cobra o pedido no gateway e, se aprovado, confirma o pedido.

    Devolve True se o pagamento foi aprovado e False se foi recusado. O service
    só conhece GatewayDePagamento; o fornecedor real fica atrás de um Adapter.

    Antes de cobrar, o Pedido confirma que está ABERTO e com pagamento PENDENTE,
    para não cobrar de novo um pedido já processado. Pagamento recusado também é
    salvo: o pedido continua ABERTO, mas não pode mais ser confirmado. Se o
    gateway falhar (GatewayIndisponivel), nada é salvo e o pagamento continua
    PENDENTE. Na Fase 1 a disponibilidade do ticket é lida aqui e passada ao
    Pedido; vender o ticket e concluir a venda fica para os eventos da Fase 2.
    """
    pedido = repo_pedidos.get(pedido_id)
    if pedido is None:
        raise RecursoNaoEncontrado(f"pedido {pedido_id} não existe")
    ticket = repo_tickets.get(pedido.ticket_id)
    if ticket is None:
        raise RecursoNaoEncontrado(f"ticket {pedido.ticket_id} não existe")
    pedido.exigir_cobranca_pendente()
    aprovado = gateway.cobrar(pedido.id, pedido.pagamento.valor, token_pagamento)
    if aprovado:
        pedido.aprovar_pagamento()
        pedido.confirmar(ticket.status)
    else:
        pedido.recusar_pagamento()
    session.commit()
    return aprovado


def cancelar_pedido(
    pedido_id: str,
    repo_pedidos: AbstractRepository[model.Pedido],
    session,
) -> None:
    pedido = repo_pedidos.get(pedido_id)
    if pedido is None:
        raise RecursoNaoEncontrado(f"pedido {pedido_id} não existe")
    pedido.cancelar()
    session.commit()
