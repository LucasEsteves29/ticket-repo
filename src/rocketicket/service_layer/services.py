from decimal import Decimal

from rocketicket.adapters.repository import AbstractRepository, AbstractVendaRepository
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


# criar_anuncio: Igor

def criar_anuncio(
    id: str,
    ticket_id: str,
    vendedor_id: str,
    preco: Decimal,
    repo_vendas: AbstractRepository[model.Venda],
    repo_tickets: AbstractRepository[model.Ticket],
    session,
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
    )
    repo_vendas.add(venda)
    session.commit()
    return venda.id


# alterar_preco e cancelar_anuncio: Miguel


# criar_pedido, confirmar_pedido e cancelar_pedido: Guilherme


def criar_pedido(
    id: str,
    ticket_id: str,
    comprador_id: str,
    repo_pedidos: AbstractRepository[model.Pedido],
    repo_vendas: AbstractVendaRepository,
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
    pagamento_aprovado: bool,
    repo_pedidos: AbstractRepository[model.Pedido],
    repo_tickets: AbstractRepository[model.Ticket],
    session,
) -> None:
    """Registra a resposta do pagamento e, se aprovado, confirma o pedido.

    Pagamento recusado também é salvo: o pedido continua ABERTO, mas não pode
    mais ser confirmado. Na Fase 1 a disponibilidade do ticket é lida aqui e
    passada ao Pedido; vender o ticket e concluir a venda fica para os eventos
    da Fase 2.
    """
    pedido = repo_pedidos.get(pedido_id)
    if pedido is None:
        raise RecursoNaoEncontrado(f"pedido {pedido_id} não existe")
    ticket = repo_tickets.get(pedido.ticket_id)
    if ticket is None:
        raise RecursoNaoEncontrado(f"ticket {pedido.ticket_id} não existe")
    if pagamento_aprovado:
        pedido.aprovar_pagamento()
        pedido.confirmar(ticket.status)
    else:
        pedido.recusar_pagamento()
    session.commit()


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
