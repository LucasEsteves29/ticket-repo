Nomes:
- Lucas Esteves
- Igor Leal
- Miguel Duque
- Caio Jose Carneiro
- Guilherme Boechat

# Dominio escolhido: Revenda de Ingressos

# Entidades de negocio:

- Ticket
- Evento
- Usuario
- Pedido
- Venda
- Pagamento

# Agregados previstos

### Ticket
- Raiz: Ticket
- Invariante: um ticket só pode ser marcado como usado se já foi vendido; não pode ser revendido depois de usado; pode ser usado apenas uma vez.
- Responsável: Lucas + Caio

### Venda
- Raiz: Venda
- Invariante: o preço de revenda não pode ultrapassar 110% do valor original do ticket; um ticket não pode estar em mais de um anúncio ativo ao mesmo tempo, uma venda cancelada ou concluida nao pode ser reativada ou ter preço alterado
- Responsável: Igor + Miguel

### Pedido
- Raiz: Pedido
- Invariante: um pedido só é confirmado se o pagamento foi aprovado e o ticket ainda estava disponível no momento da confirmação, u   m pedido cancelado ou já confirmado não pode ser confirmado novamente nem ter o pagamento alterado.
- Responsável: Guilherme