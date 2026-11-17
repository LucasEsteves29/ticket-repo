# ADR 0002 — Testes com FakeRepository

- **Status:** Aceita
- **Data:** 2026-11-16
- **Autor:** Caio Jose Carneiro (@caiojosesouz-dotcom)

## Contexto

Os casos de uso do RocketTicket coordenam as regras dos agregados Ticket, Venda e
Pedido e usam repositórios para guardar e buscar os objetos. Testar cada cenário
somente com o repositório SQLAlchemy exigiria preparar tabelas, iniciar mapeadores e
abrir sessões mesmo quando o objetivo fosse verificar uma regra de negócio, como
impedir a emissão de um Ticket com ID repetido.

Na Fase 1, já existia um contrato de repositório separado da implementação de
persistência. Era necessário escolher como testar os casos de uso sem depender do
banco e sem acoplar as verificações às chamadas internas do ORM.

Este ADR registra retrospectivamente a decisão aplicada em `7df0ec4` (Caio,
28/09/2026), que criou o `FakeTicketRepository` em `tests/conftest.py`. O adaptador
real foi implementado em `c13cc33`, e os testes do repositório em `c78e9ed`, ambos
também de 28/09. O uso do fake nos testes de `emitir_ticket` aparece em `dba9d57`
(29/09), anterior à refatoração de injeção de dependência da Fase 2.

## Decisão

Usar implementações em memória dos contratos de repositório nos testes unitários
dos casos de uso. Os fakes ficam em `tests/conftest.py` e são entregues por fixtures
do pytest, criando um estado independente para cada teste.

O `FakeTicketRepository` guarda objetos de domínio em um conjunto, implementa
`add()` e `get()` e permite listar os Tickets por ID. Na Fase 1, herdava de
`AbstractRepository[Ticket]`; na versão atual, herda de `AbstractTicketRepository`,
que explicita também o contrato de listagem. Os fakes de Venda e Pedido seguem a
mesma estratégia, respeitando os contratos de seus clientes.

Os testes chamam os services reais e verificam os resultados e as exceções de
domínio. Por exemplo, `tests/unit/test_services_ticket.py` verifica que
`emitir_ticket` salva os dados e o status corretos, devolve o ID e rejeita um ID
repetido sem substituir o Ticket existente. O service recebe o fake por parâmetro;
não é necessário substituir a classe SQLAlchemy com um patch.

O repositório, real ou fake, não faz commit. Nos testes unitários, a `FakeSession`
registra se o service chamou `commit()`. Isso verifica a intenção de confirmar a
operação, sem simular o funcionamento de uma transação de banco.

Manter os testes de integração com SQLAlchemy e SQLite em memória. Em
`tests/integration/test_ticket_repository.py`, os cenários de gravação, busca e
listagem exercitam o adaptador real; `expunge_all()` nos cenários de persistência
permite conferir objetos recarregados do banco. O mesmo arquivo verifica operações
do fake, mas não constitui uma suíte de contrato parametrizada entre os adaptadores.

## Alternativas

- **Usar SQLAlchemy com SQLite em todos os testes dos services.** Exercitaria a
  persistência em cada cenário, mas exigiria tabelas, sessões e mapeadores para
  verificar regras que podem ser testadas em memória. SQLite continua sendo usado
  nos testes de integração, onde essa preparação é necessária.
- **Usar mocks do repositório ou da sessão.** Permitiria configurar respostas e
  verificar chamadas isoladas, mas cada cenário precisaria programar essas respostas.
  Um fake com estado permite adicionar um Ticket, executar o caso de uso e consultar
  o resultado usando o mesmo contrato. Mocks continuam possíveis quando o objetivo
  específico for verificar uma interação.
- **Usar o banco de produção nos testes unitários.** Aumentaria a fidelidade ao
  ambiente real, mas acrescentaria configuração de serviço, limpeza de dados e
  dependência de sua disponibilidade. Verificações específicas desse banco devem
  ficar em uma camada de integração própria, sem substituir os testes unitários.

## Consequências

Positivas:
- Os casos de uso podem ser testados sem criar tabelas, abrir conexões ou iniciar os
  mapeadores ORM. As entidades exercitadas são as mesmas classes usadas em produção.
- As fixtures isolam o estado dos cenários, e o teste expressa os dados de entrada,
  a operação e seu resultado, sem precisar conhecer consultas SQLAlchemy.
- O contrato do repositório permite trocar o adaptador entregue ao service sem
  alterar a regra de negócio. Essa escolha também deu suporte à injeção posterior
  do repositório de Ticket nas rotas HTTP.

Negativas e cuidados:
- Há uma implementação adicional a manter. Uma mudança no contrato ou em uma consulta
  precisa ser refletida tanto no adaptador real quanto no fake; herdar da abstração
  ajuda a cobrar os métodos, mas não garante equivalência de comportamento.
- O conjunto em memória não reproduz restrições de chave primária, conversões de
  `Decimal` e Enum, carregamento de relacionamentos ou concorrência do banco.
  Verificar uma regra com o fake não comprova que ela será persistida corretamente.
- A `FakeSession` não executa flush nem rollback. Testes de integração continuam
  responsáveis por conferir as transações, inclusive a gravação conjunta e o
  rollback do check-in e de sua auditoria na versão atual.
- SQLite também tem diferenças em relação a outros bancos. Os testes existentes
  cobrem o adaptador nesse ambiente; requisitos específicos de outro banco exigem
  verificações adicionais nele.
