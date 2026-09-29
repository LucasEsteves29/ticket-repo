# DECISIONS.md

Registro das decisões de projeto do RocketTicket. Cada checkpoint tem uma subseção
por integrante, escrita pela própria pessoa: o que implementou, em quais arquivos,
em quais commits e as decisões de projeto que tomou.

---

# Parte 1 — Fase 1

## fase1-checkpoint-1 — Modelo de domínio

### Lucas Esteves (@LucasEsteves29)

**O que fiz:** montei a estrutura inicial do repositório seguindo o Apêndice B
(pacote rocketicket em src/, pastas domain/, adapters/, service_layer/,
entrypoints/ e tests/) e o workflow de CI, com um smoke test para a pipeline
não falhar com a pasta de testes vazia. No agregado Ticket, implementei a classe
Ticket com o enum StatusTicket, os métodos anunciar() e vender() e as
exceções ErroDeDominio (base de todas), TicketJaAnunciado, TicketJaUsado,
TicketNaoAnunciado e CompraDoProprioTicket. Escrevi os testes unitários de
emissão, anunciar() e vender().

**Arquivos:** src/rocketicket/domain/model.py, tests/unit/test_ticket.py,
tests/unit/test_smoke.py, .github/workflows/ci.yml

**Decisões:**
- O ticket nasce VENDIDO, e não DISPONIVEL, porque a emissão já é uma venda:
  a do organizador para o primeiro dono. Se ele nascesse disponível, quem compra
  do organizador e nunca revende nunca chegaria a um estado que satisfaz "só pode
  usar se foi vendido", e não conseguiria fazer check-in.
- A regra "um ticket não pode estar em mais de um anúncio ativo" ficou no
  agregado Ticket (anunciar() falha se já está ANUNCIADO), e não na Venda,
  porque a raiz Venda só enxerga a si mesma e não conseguiria garantir a regra sem
  consultar as outras vendas.

### Caio Jose Carneiro (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

### Igor Leal (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

### Miguel Duque (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

### Guilherme Boechat (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

---

## fase1-checkpoint-2 — Repository Pattern

### Lucas Esteves (@LucasEsteves29)

**O que fiz:** criei o mapeamento ORM imperativo em orm.py: o registry, o
helper _enum_por_valor(), a tabela tickets e o start_mappers(), com blocos
reservados para a Venda e o Pedido. Em repository.py, criei a
AbstractRepository genérica com add() e get(). Nos testes, escrevi as
fixtures in_memory_db e session no conftest.py e os testes de integração do
mapeamento do Ticket em test_orm.py, e atualizei a CI para rodar também
tests/integration. Também corrigi o alterar_preco() da Venda, que ainda usava o
cálculo antigo do teto de 110%, e adicionei os testes que distinguem o teto
arredondado do exato.

**Arquivos:** src/rocketicket/adapters/orm.py,
src/rocketicket/adapters/repository.py, tests/conftest.py,
tests/integration/test_orm.py, .github/workflows/ci.yml,
src/rocketicket/domain/model.py, tests/unit/test_venda.py

**Decisões:**
- Os status são gravados no banco pelo valor do enum ("vendido"), e não pelo
  nome ("VENDIDO"), que é o padrão do SQLAlchemy. O valor é o que o domínio já
  expõe nas mensagens de erro e o que a API devolve em JSON, então o banco fica
  consistente com o resto do sistema. A coluna usa native_enum=False com
  create_constraint=True, o que gera um CHECK no banco: um status inválido é
  recusado mesmo quando inserido por SQL puro, como verifica um dos testes.
- Fiz uma única AbstractRepository genérica (Generic[T]), em vez de uma classe
  abstrata por agregado. Mudanças no contrato comum ficam em um lugar só, e quem
  precisa de uma consulta extra, como a Venda com get_ativa_por_ticket(), cria
  uma abstração própria herdando dela.
- Nos testes de integração, depois de salvar faço commit e expunge_all(), e
  comparo campo a campo. Sem isso, o get() devolveria o próprio objeto que
  estava na memória, e como o __eq__ do domínio compara só o id, o teste
  passaria mesmo com o mapeamento errado.
- No teto de 110%, o preço máximo é arredondado para baixo até o centavo. O banco
  guarda duas casas decimais e arredondaria para cima um teto como 109,989, o que
  faria uma venda voltar do banco acima do limite. Os testes com 109,985 são os
  únicos que diferenciam o teto arredondado do exato.

### Caio Jose Carneiro (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

### Igor Leal (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

### Miguel Duque (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

### Guilherme Boechat (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

---

## fase1-entrega — Service layer e API Flask

### Lucas Esteves (@LucasEsteves29)

**O que fiz:** implementei o caso de uso emitir_ticket em services.py, com a
exceção TicketJaExiste e a base ErroDeServico para os erros da camada de
serviço, e deixei blocos reservados para os casos de uso dos outros agregados. Nos
testes, criei a FakeSession no conftest.py e os testes unitários do service
com os Fakes. Combinei com o Igor de ficar com a base da API: create_app(), o
start_mappers(), a sessão por requisição e o tratamento central de erros no
flask_app.py, além da fixture client para os testes e2e. Em cima dela, fiz o
endpoint POST /tickets com os testes e2e, e a CI passou a rodar a suíte inteira.

**Arquivos:** src/rocketicket/service_layer/services.py,
src/rocketicket/entrypoints/flask_app.py, tests/conftest.py,
tests/unit/test_services_ticket.py, tests/e2e/test_ticket_api.py,
.github/workflows/ci.yml

**Decisões:**
- Os services recebem só tipos primitivos (str, Decimal), nunca objetos do
  domínio. Assim a API não precisa conhecer as classes do model.py, e o
  service é o único lugar que monta e manipula os agregados.
- Separei os erros da camada de serviço (ErroDeServico) dos erros do domínio
  (ErroDeDominio). Um id duplicado não é uma invariante do Ticket, e sim uma
  regra de uso do sistema. Com as duas bases, o flask_app.py traduz cada uma
  para um código HTTP num lugar só (400 para domínio, 409 para serviço), e nenhum
  endpoint precisa de try/except próprio.
- O create_app() recebe a fábrica de sessões de fora. A aplicação real passa o
  banco de verdade e os testes e2e passam um SQLite em memória, sem nenhuma
  condição especial para teste dentro do app.
- O valor_original chega como string no JSON (ex.: "150.00") e é convertido
  para Decimal. Número em JSON vira float no Python, e o erro de arredondamento
  apareceria justamente no teto de 110% da revenda.

### Caio Jose Carneiro (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

### Igor Leal (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

### Miguel Duque (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

### Guilherme Boechat (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

