"""Auditoria persistida na mesma transação que a alteração do Ticket."""

from rocketicket.adapters.orm import checkins
from rocketicket.adapters.repository import RegistroCheckIn


class SqlAlchemyCheckInAudit:
    def __init__(self, session):
        self.session = session

    def __call__(self, registro: RegistroCheckIn) -> None:
        self.session.execute(checkins.insert().values(
            ticket_id=registro.ticket_id,
            dono_id=registro.dono_id,
            ocorrido_em=registro.ocorrido_em,
        ))
