## Responsabilidades

| Integrante | Usuário GitHub | Agregado / Módulo |
| :--- | :--- | :--- |
| Igor Leal | @igorbleal | Agregado Venda |
| Miguel Duque | @miguelduq | Agregado Venda |
| Lucas Esteves | @LucasEsteves29 | Agregado Ticket |
| Caio Jose Carneiro | @caiojosesouz-dotcom | Agregado Ticket |
| Guilherme Boechat | @guilhermeboechat | Agregado Pedido |

## Check-in de Ticket (Caio)

`POST /tickets/<ticket_id>/check-in` marca um ticket vendido como usado e
retorna `200` com `{"id": "...", "status": "usado"}`. Ticket inexistente retorna
`404`; ticket já usado ou anunciado retorna `400`.

O `AuditedTicketRepository` aplica Decorator sobre o contrato de Ticket,
delegando a persistência e acrescentando um registro com ticket, dono e horário
UTC. O registro em `checkins` e a alteração do Ticket participam da mesma
transação; o serviço confirma o commit. A tabela faz parte de `orm.metadata` e
precisa ser criada também em bancos existentes antes de usar a rota.

Validação: `python -m pytest tests`.
