from decimal import Decimal

from rocketicket.adapters.repository import AbstractRepository
from rocketicket.domain import model


class ErroDeServico(Exception):
    pass


class RecursoNaoEncontrado(ErroDeServico):
    pass


class TicketJaExiste(ErroDeServico):
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


# alterar_preco e cancelar_anuncio: Miguel


# criar_pedido, confirmar_pedido e cancelar_pedido: Guilherme
