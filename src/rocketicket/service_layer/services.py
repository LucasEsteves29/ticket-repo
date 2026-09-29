from decimal import Decimal

from rocketicket.adapters.repository import AbstractRepository
from rocketicket.domain import model


class ErroDeServico(Exception):
    pass


class RecursoNaoEncontrado(ErroDeServico):
    pass


class TicketJaExiste(ErroDeServico):
    pass

class VendaJaExiste(ErroDeServico):
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
