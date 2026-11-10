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

## Confirmação de Pedido com gateway de pagamento (Guilherme)

`POST /pedidos/<pedido_id>/confirmacao` recebe `{"token_pagamento": "..."}` e cobra o
valor do pedido no gateway de pagamento externo simulado, através do
`AdaptadorGatewayExterno` (padrão Adapter, ver `docs/gof.md`). Resposta `200` com
`{"id": "...", "pagamento": "aprovado"}` ou `{"id": "...", "pagamento": "recusado"}`.

Tokens do gateway simulado: `tok_aprovado` aprova, `tok_recusado` recusa, `tok_falha`
simula o gateway fora do ar (`502`, nada é salvo e dá para tentar de novo) e qualquer
outro token é recusado. Pedido ou ticket inexistente retorna `404`. Pedido já
confirmado, cancelado ou com pagamento recusado retorna `400` sem cobrar de novo.
