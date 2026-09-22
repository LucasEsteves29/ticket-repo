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

class StatusVenda(Enum):
    ATIVA = "ativa"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class PrecoAcimaDoLimite(Exception):
    pass


class Venda:

    def __init__(
        self,
        id: str,
        ticket_id: str,
        vendedor_id: str,
        preco: float,
        valor_original: float,
    ):
        
        # validacao do preço de revenda, pois não pode passar de 110% do valor original
        limite_maximo = round(valor_original * 1.10, 2)
        if round(preco, 2) > limite_maximo:
            raise PrecoAcimaDoLimite(
                f"Preço {preco} excede o limite máximo permitido de 110% ({limite_maximo})"
            )

        self.id = id
        self.ticket_id = ticket_id
        self.vendedor_id = vendedor_id
        self.preco = preco
        self.valor_original = valor_original
        self.status = StatusVenda.ATIVA