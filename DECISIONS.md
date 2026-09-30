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

### Igor Leal (@igorbleal)
**O que fiz:** implementei a entidade Venda em model.py, o enum StatusVenda
(com os estados ATIVA, CONCLUIDA e CANCELADA) e a exceção PrecoAcimaDoLimite.
Na inicialização da Venda, implementei a validação do teto máximo de revenda de
110% do valor original utilizando Decimal com quantize e arredondamento para
baixo (ROUND_DOWN). Escrevi os testes unitários de criação válida e do teto de
110% em test_venda.py.
**Arquivos:** src/rocketicket/domain/model.py, tests/unit/test_venda.py
**Decisões:**
- A raiz Venda não valida outros anúncios do mesmo ticket porque não enxerga
  outras vendas; essa regra foi delegada ao agregado Ticket.
- O cálculo do teto de 110% é truncado para duas casas decimais com
  ROUND_DOWN. Isso evita que dízimas como 99.99 * 1.10 = 109.989 sejam
  arredondadas para cima pelo banco de dados (virando 109.99), o que faria a
  venda ultrapassar o limite permitido de 110% ao ser recarregada.

### Miguel Duque (@miguelduq)

**O que fiz:** implementei na Venda os métodos alterar_preco(), cancelar() e
concluir(), a exceção VendaEncerrada e o método auxiliar _exigir_ativa(). Em
test_venda.py, escrevi os testes de violação dessas operações: alterar o preço
de uma venda cancelada ou concluída, novo preço acima de 110%, preço recusado
mantendo o anterior, cancelar ou concluir duas vezes e tentar reativar uma venda
encerrada (concluir uma cancelada e cancelar uma concluída).

**Arquivos:** src/rocketicket/domain/model.py, tests/unit/test_venda.py

**Decisões:**
- Uma única exceção, VendaEncerrada, para qualquer operação em venda CANCELADA
  ou CONCLUIDA, em vez de uma exceção por estado. A regra do domínio é a mesma
  ("venda encerrada não muda mais"), e a mensagem já informa o status atual e a
  ação que foi recusada.
- A checagem fica em _exigir_ativa(), chamada na primeira linha de
  alterar_preco(), cancelar() e concluir(). A regra fica em um lugar só, e a
  validação acontece antes de qualquer mudança de estado: uma operação recusada
  não deixa a venda pela metade, como os testes verificam conferindo que o preço
  e o status continuam os mesmos.
- Não existe um método reativar(). CANCELADA e CONCLUIDA são estados finais, e
  os únicos caminhos que mexeriam no status de uma venda encerrada, cancelar() e
  concluir(), também são bloqueados. Os testes de "reativar" cobrem exatamente
  esses dois caminhos.
- alterar_preco() respeita o mesmo teto de 110% da criação. Sem isso, bastaria
  criar o anúncio com um preço válido e depois subir o preço para burlar a regra.

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

### Igor Leal (@igorbleal)

**O que fiz:** Criei a tabela vendas no orm.py e a função _mapear_venda() com o
mapeamento imperativo da entidade Venda, registrando-a dentro de start_mappers().
No conftest.py, implementei a classe FakeVendaRepository herdando de
AbstractVendaRepository com os métodos add(), get() e get_ativa_por_ticket(),
viabilizando os testes unitários do serviço. Em test_orm.py, escrevi a classe
TestMapeamentoVenda com os testes de integração do mapeamento, verificando a
persistência e recuperação campo a campo, o salvamento do status como valor
do enum em minúsculas, a integridade dos tipos Decimal para valores monetários
e a rejeição de status fora do enum no banco.

**Arquivos:** src/rocketicket/adapters/orm.py, tests/conftest.py,
tests/integration/test_orm.py

**Decisões:**
- As colunas de preço e valor original na tabela vendas usam Numeric(10, 2),
  garantindo precisão monetária de 2 casas decimais e compatibilidade com o
  Decimal do domínio.
- O FakeVendaRepository implementa get_ativa_por_ticket() filtrando a coleção
  em memória por ticket_id e StatusVenda.ATIVA, mantendo a paridade de
  comportamento exata com a consulta executada pelo SqlAlchemyVendaRepository no banco.

### Miguel Duque (@miguelduq)

**O que fiz:** em repository.py, criei a AbstractVendaRepository, que herda de
AbstractRepository[model.Venda] e acrescenta get_ativa_por_ticket(ticket_id),
e o SqlAlchemyVendaRepository, com add(), get() e get_ativa_por_ticket()
usando a tabela vendas mapeada pelo Igor. Escrevi os testes de integração do
repositório em test_venda_repository.py, contra o SQLite em memória: venda
salva voltando campo a campo, get() de id inexistente, add() sem commit e
get_ativa_por_ticket() ignorando vendas canceladas, concluídas e de outros
tickets, além de achar a venda ativa quando o mesmo ticket tem uma venda antiga
cancelada e uma nova.

**Arquivos:** src/rocketicket/adapters/repository.py,
tests/integration/test_venda_repository.py

**Decisões:**
- get_ativa_por_ticket() fica numa abstração própria da Venda
  (AbstractVendaRepository), e não na AbstractRepository genérica, porque só a
  Venda precisa dessa consulta. Assim o Fake também é obrigado a implementá-la:
  o FakeVendaRepository herda dela. É essa consulta que o criar_pedido usa para
  achar o anúncio ativo do ticket.
- O SqlAlchemyVendaRepository recebe a sessão pronta no construtor e não importa
  o SQLAlchemy no topo do arquivo. O conftest.py importa repository.py, e os
  testes unitários não podem carregar o banco.
- O repositório nunca faz commit: add() só entrega a venda à sessão, e quem
  confirma a transação é o chamador. Um teste verifica isso fazendo add() e
  rollback() e conferindo que a tabela continua vazia.
- A venda ativa é filtrada no próprio banco, por ticket_id e status ATIVA, em
  vez de carregar todas as vendas do ticket e filtrar em Python. Um ticket pode
  acumular várias vendas encerradas ao longo das revendas, e só uma pode estar
  ativa.

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

### Igor Leal (@igorbleal)

**O que fiz:** implementei o caso de uso criar_anuncio em services.py, com a
exceção VendaJaExiste herdando de ErroDeServico. O serviço busca o ticket no
repositório de tickets, valida se ele existe, invoca ticket.anunciar() para
garantir as invariantes de ciclo de vida do ticket, cria a entidade Venda com
o valor_original obtido diretamente do ticket (validando o teto de 110%) e
persiste no repositório de vendas confirmando na sessão. Escrevi os testes
unitários da camada de serviço em test_services_venda.py utilizando apenas os
Fakes (FakeTicketRepository, FakeVendaRepository e FakeSession). Na camada de
entrada, criei o endpoint POST /anuncios no flask_app.py, validando o JSON de
entrada com os helpers centrais da API e chamando o service com as sessões e
repositórios adequados. Por fim, escrevi a suíte de testes de ponta a ponta (e2e)
em test_venda_api.py cobrindo criação com sucesso, validação de campos
obrigatórios, preço inválido, duplicidade de ID, ticket inexistente, ticket já
anunciado e violação do teto de 110%.

**Arquivos:** src/rocketicket/service_layer/services.py,
src/rocketicket/entrypoints/flask_app.py,
tests/unit/test_services_venda.py,
tests/e2e/test_venda_api.py

**Decisões:**
- O endpoint POST /anuncios e o serviço criar_anuncio não recebem o valor_original
  no payload, apenas ticket_id, vendedor_id e preco. O service busca o ticket
  no repositório e obtém o valor_original diretamente da entidade Ticket. Isso
  impede que um cliente mal-intencionado envie um valor original falso para
  burlar a regra do teto de 110%.
- A regra de que o ticket não pode estar em dois anúncios ativos ao mesmo tempo
  continua delegada ao próprio agregado Ticket: ao chamar ticket.anunciar(), o
  Ticket lança TicketJaAnunciado se já estiver anunciado (ou TicketJaUsado se já
  foi consumido). O flask_app.py captura esse ErroDeDominio centralmente e
  retorna HTTP 400 sem necessidade de try/except na rota.
- Caso o ticket informado não exista, o serviço lança RecursoNaoEncontrado
  (subclasse de ErroDeServico), traduzido centralmente pelo Flask para HTTP 404.
  Já se o id da Venda for repetido, lança VendaJaExiste, traduzido para HTTP 409
  (Conflict), garantindo consistência semântica com o POST /tickets.
- O preço do anúncio chega como string no JSON e é validado com _ler_decimal(),
  garantindo conversão estrita para Decimal antes de entrar no service e no
  domínio, eliminando qualquer risco de inconsistência de ponto flutuante.a aman

### Miguel Duque (@miguelduq)

**O que fiz:**

**Arquivos:**

**Decisões:**

### Guilherme Boechat (@usuario-github)

**O que fiz:**

**Arquivos:**

**Decisões:**

