# ADR 0004 — Consulta extra em abstração própria

- **Status:** Aceita
- **Data:** 2026-10-22 (registra decisão tomada em 28/09/2026, na Fase 1)
- **Autor:** Miguel Duque (@miguelduq)

## Contexto

A AbstractRepository genérica do projeto (`adapters/repository.py`) define só o
contrato mínimo de todo repositório: `add()` e `get(id)`. A Venda precisa de uma
consulta a mais: achar o anúncio **ativo** de um ticket, sabendo apenas o
`ticket_id`. Um ticket acumula várias vendas ao longo das revendas (canceladas e
concluídas), mas no máximo uma pode estar ATIVA. Essa consulta é usada hoje pelo
`criar_pedido` (`service_layer/services.py`), que recebe o `ticket_id` do
comprador e precisa da venda ativa para saber o preço.

Os testes unitários dos services usam repositórios falsos em memória (Fakes, em
`tests/conftest.py`), e os de integração usam o repositório real contra SQLite em
memória. A consulta precisa existir nos dois.

## Decisão

Criar uma abstração própria da Venda, `AbstractVendaRepository`, que herda de
`AbstractRepository[model.Venda]` e acrescenta o método abstrato
`get_ativa_por_ticket(ticket_id) -> Venda | None`. O repositório real
(`SqlAlchemyVendaRepository`) e o falso (`FakeVendaRepository`) herdam dela, e os
services que precisam da consulta recebem `AbstractVendaRepository` na assinatura.

No repositório real, o filtro por `ticket_id` e `status = ATIVA` é feito no banco
(`filter_by(...).first()`), e não em Python.

Commits: `73b9847` (abstração) e `54e16d6` (implementação com SQLAlchemy), com os
testes de integração em `ed46d50`.

## Alternativas

1. **Colocar `get_ativa_por_ticket()` na AbstractRepository genérica.** Rejeitada:
   Ticket e Pedido seriam obrigados a implementar uma consulta que não faz
   sentido para eles. O contrato comum deixaria de ser comum.
2. **Implementar o método só no `SqlAlchemyVendaRepository`, sem abstração.**
   Rejeitada: nada obrigaria o Fake a ter o mesmo método. Um service que
   chamasse a consulta passaria no teste de integração e quebraria no unitário
   (ou o contrário), e o erro só apareceria na execução.
3. **Fazer a consulta direto na sessão do SQLAlchemy, dentro do service.**
   Rejeitada: o service passaria a depender do ORM, e os testes unitários não
   poderiam mais usar Fakes. É exatamente o acoplamento que a camada de
   repositório existe para evitar.
4. **Adicionar um `list()` genérico e filtrar a venda ativa em Python.** Rejeitada:
   carregaria todas as vendas do ticket (ou de todos os tickets) para usar uma,
   e espalharia a regra "venda ativa = status ATIVA" por quem chamasse.

## Consequências

**Positivas**
- O contrato fica explícito: qualquer repositório de Venda, real ou falso, é
  obrigado pelo `abc` a implementar a consulta. Uma classe que esqueça o método
  nem chega a ser instanciada.
- O `FakeVendaRepository` (Igor, `46e1abf`) foi escrito em cima dessa abstração, e
  o `criar_pedido` (Guilherme) usou a consulta sem precisar conhecer o SQLAlchemy.
- A regra de filtro fica num lugar só por implementação, e os testes de
  integração (`ed46d50`) cobrem os casos em que ela poderia errar: venda
  cancelada, concluída, de outro ticket e a ativa entre uma antiga cancelada e
  uma nova.

**Negativas**
- Mais uma classe e mais um nível de herança para uma única consulta.
- Cada consulta nova da Venda exige mudar três lugares: a abstração, o
  repositório real e o Fake.
- O Fake reimplementa o filtro em Python. Se a regra mudar (por exemplo, um novo
  status que também conte como "ativo"), as duas implementações podem divergir.
  Só os testes de integração pegam essa divergência, e eles não rodam contra o Fake.
