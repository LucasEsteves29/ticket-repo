# ADR 0005 — Pagamento dentro do Pedido

- **Status:** Aceita
- **Data:** 2026-10-22 (registra decisão tomada em 22/09/2026, na Fase 1)
- **Autor:** Guilherme Boechat (@guilhermeboechat)

## Contexto

A `PROPOSTA.md` lista Pagamento como entidade de negócio, ao lado do Pedido, mas a
invariante do Pedido depende diretamente dele: um pedido só é confirmado se o
pagamento foi aprovado e o ticket ainda estava disponível, e um pedido cancelado ou
já confirmado não pode ser confirmado de novo nem ter o pagamento alterado. A regra
mistura o estado do pedido com o estado do pagamento.

Cada pedido tem exatamente um pagamento, criado junto com ele e com o mesmo valor (o
preço do anúncio ativo, lido no `criar_pedido`). Nenhum caso de uso consulta o
pagamento sozinho: `criar_pedido`, `confirmar_pedido` e `cancelar_pedido`
(`service_layer/services.py`) partem todos do id do pedido. Também não existe
integração com meio de pagamento na Fase 1; o `confirmar_pedido` recebe
`pagamento_aprovado`, que simula essa resposta.

Era preciso decidir se o Pagamento seria um agregado próprio, com raiz e
repositório, ou uma entidade interna do Pedido.

## Decisão

O Pagamento é uma entidade interna do agregado Pedido (`domain/model.py`). O Pedido
cria o Pagamento no construtor, com o valor do pedido, e é o único caminho para
mexer nele: `aprovar_pagamento()` e `recusar_pagamento()` chamam `_exigir_aberto()`
antes de delegar ao Pagamento. O Pagamento cuida só da própria regra, a de sair de
PENDENTE uma única vez, para APROVADO ou RECUSADO (`PagamentoJaProcessado`). O
`confirmar()` lê `pagamento.status` direto, sem depender de nada de fora do
agregado além do status do ticket que o service passa.

Na persistência (`adapters/orm.py`), o agregado continua inteiro:

- A tabela `pagamentos` usa o `pedido_id` como chave primária (um pagamento por
  pedido), com FK para `pedidos`. A FK é permitida porque liga duas tabelas do
  mesmo agregado; entre agregados continuam só os ids.
- A relação `pedido.pagamento` usa `uselist=False`, `lazy="joined"` e
  `cascade="all, delete-orphan"`: salvar o Pedido salva o Pagamento, e carregar o
  Pedido traz o Pagamento na mesma consulta.
- Não existe repositório de Pagamento. O `SqlAlchemyPedidoRepository` e o
  `FakePedidoRepository` cuidam dos dois.

Commits: `023d0e3` e `5614b72` (Pagamento e status do pedido), `d9ef901`
(`confirmar()`, `cancelar()` e transições do Pagamento), `624adca` (tabelas e
mapeamento) e `e9c0223` (FakePedidoRepository e testes de integração).

## Alternativas

1. **Pagamento como agregado próprio, com repositório e referência ao pedido por
   id.** Rejeitada: a invariante passaria a cruzar dois agregados. O Pedido não
   enxergaria o pagamento, então o service teria que ler o status e passar para o
   `confirmar()`, como já acontece com o ticket. E nada impediria aprovar o
   pagamento de um pedido cancelado direto pelo repositório de pagamentos, já que a
   regra "pedido encerrado não muda de pagamento" ficaria do lado do Pedido. Ainda
   seriam mais um repositório e mais um Fake para manter.
2. **Guardar o status do pagamento como atributo do próprio Pedido
   (`status_pagamento`), sem classe Pagamento.** Rejeitada: daria uma tabela a
   menos, mas o Pedido ficaria com dois ciclos de vida na mesma classe, e a regra
   "sai de PENDENTE uma vez só" se misturaria com as regras do pedido. Separado,
   cada classe cuida do seu ciclo, e o Pagamento já tem onde crescer quando houver
   integração real (id da transação, meio de pagamento).
3. **Dar um id próprio ao Pagamento.** Rejeitada: ninguém busca pagamento pelo id,
   e um id de domínio sugeriria que ele pode ser referenciado de fora do Pedido.
   Usar o `pedido_id` como chave também garante no banco que não existem dois
   pagamentos para o mesmo pedido.

## Consequências

**Positivas**
- A invariante inteira é verificada dentro do agregado e coberta por testes
  unitários sem banco (`tests/unit/test_pedido.py`): alterar o pagamento de um
  pedido confirmado ou cancelado falha e o status do pagamento não muda; confirmar
  com pagamento pendente ou recusado lança `PagamentoNaoAprovado`.
- O agregado entra e sai inteiro pela raiz: um `add()` do Pedido grava as duas
  tabelas, e um `get()` devolve o pedido com o pagamento já carregado. Os testes de
  integração (`test_orm.py` e `test_pedido_repository.py`) cobrem os dois casos.
- No `confirmar_pedido`, aprovar o pagamento e confirmar o pedido vão no mesmo
  commit. Se o `confirmar()` lançar `TicketIndisponivel`, o commit não acontece e
  a aprovação também não é salva.
- Um repositório e um Fake a menos.

**Negativas**
- O Pagamento não pode ser lido nem alterado sem carregar o Pedido. Se aparecer um
  caso de uso que parta do pagamento (por exemplo, um retorno do meio de pagamento
  que só informa o id da transação), vai ser preciso uma consulta nova no
  repositório de pedidos ou rever esta decisão.
- Um pedido tem um único pagamento. Depois de uma recusa, o pedido fica ABERTO mas
  só pode ser cancelado, e uma nova tentativa exige um pedido novo. Permitir várias
  tentativas no mesmo pedido mudaria o modelo (lista de pagamentos) e a chave da
  tabela `pagamentos`.
- O `lazy="joined"` faz um JOIN em todo `get()` do pedido, mesmo quando o
  pagamento não é usado, como no `cancelar_pedido`. O custo é pequeno com uma linha
  de pagamento por pedido.
- A FK `pagamentos -> pedidos` é uma exceção à regra "sem FK" do `orm.py`, e quem
  mexer no mapeamento precisa saber que ela só vale dentro do agregado.
