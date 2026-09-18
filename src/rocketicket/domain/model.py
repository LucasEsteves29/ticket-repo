from enum import Enum


class StatusTicket(Enum):
    DISPONIVEL = "disponivel"
    A_VENDA = "a_venda"
    VENDIDO = "vendido"
    USADO = "usado"


class TicketNaoPodeSerUsado(Exception):
    pass


class Ticket:
    def __init__(self, id: str, evento_id: str):
        self.id = id
        self.evento_id = evento_id
        self.status = StatusTicket.DISPONIVEL

    def marcar_como_usado(self):
        # sua lógica aqui
        ...