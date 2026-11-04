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

### Guilherme Boechat (@guilhermeboechat)

**O que fiz:** implementei o agregado Pedido em model.py: o Pagamento como
entidade interna do Pedido, os enums StatusPagamento (PENDENTE, APROVADO,
RECUSADO) e StatusPedido (ABERTO, CONFIRMADO, CANCELADO) e a raiz Pedido, com
aprovar_pagamento(), recusar_pagamento(), confirmar() e cancelar(). Criei as
exceções PagamentoJaProcessado, PagamentoNaoAprovado, TicketIndisponivel e
PedidoEncerrado. Escrevi os testes unitários em test_pedido.py, cobrindo as
transições válidas e as violações de invariante com pytest.raises.

**Arquivos:** src/rocketicket/domain/model.py, tests/unit/test_pedido.py

**Decisões:**
- O Pagamento mora dentro do agregado Pedido e só muda pela raiz:
  aprovar_pagamento() e recusar_pagamento() checam antes se o pedido ainda está
  ABERTO. O Pagamento cuida só da própria regra, a de sair de PENDENTE uma única
  vez, para APROVADO ou RECUSADO.
- confirmar() recebe o status do ticket como parâmetro, em vez de acessar o
  Ticket. O Pedido não enxerga outro agregado, então quem lê o ticket e passa o
  status é o service. "Disponível para compra" é ANUNCIADO, e não DISPONIVEL,
  que nenhum ticket alcança.
- O Pedido tem um status próprio, separado do status do pagamento. A regra
  "pedido confirmado ou cancelado não pode ser confirmado de novo nem ter o
  pagamento alterado" fica num lugar só, em _exigir_aberto(), chamado no início
  de cada operação.
- Os testes chegam a todos os estados pela API do domínio, sem atribuir status
  na mão, para continuarem válidos quando o agregado for encapsulado.

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

### Guilherme Boechat (@guilhermeboechat)

**O que fiz:** criei as tabelas pedidos e pagamentos e a função
_mapear_pedido() em orm.py, chamada no start_mappers(), com a relação
pedido.pagamento. Em repository.py, criei o SqlAlchemyPedidoRepository com
add() e get(), e no conftest.py o FakePedidoRepository. Em test_orm.py, escrevi
a classe TestMapeamentoPedido: pedido salvo voltando campo a campo, pagamento
voltando junto com o pedido, status gravados pelo valor do enum, valor voltando
como Decimal e o banco recusando status inválido de pedido e de pagamento. Em
test_pedido_repository.py, escrevi os testes do repositório contra o SQLite em
memória: add() gravando pedido e pagamento, add() sem commit, get() trazendo o
pagamento, get() de id inexistente e mudanças de estado persistidas após o
commit.

**Arquivos:** src/rocketicket/adapters/orm.py,
src/rocketicket/adapters/repository.py, tests/conftest.py,
tests/integration/test_orm.py, tests/integration/test_pedido_repository.py

**Decisões:**
- O Pagamento não tem id no domínio, então a chave da tabela pagamentos é o
  próprio pedido_id (um pagamento por pedido). A FK pagamentos -> pedidos é
  permitida porque liga duas tabelas do mesmo agregado; entre agregados
  continuam só os IDs, sem FK.
- A relação pedido.pagamento usa cascade="all, delete-orphan" e lazy="joined".
  Salvar o Pedido salva o Pagamento, carregar o Pedido traz o Pagamento na mesma
  consulta e não existe repositório de Pagamento: o agregado entra e sai inteiro
  pela raiz.
- O repositório tem só add() e get(), porque todos os casos de uso do Pedido
  partem do id. Como os outros repositórios, ele nunca faz commit, e um teste
  verifica isso com add() seguido de rollback().

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

### Guilherme Boechat (@guilhermeboechat)

**O que fiz:** implementei os casos de uso criar_pedido, confirmar_pedido e
cancelar_pedido em services.py, com a exceção PedidoJaExiste herdando de
ErroDeServico. Escrevi os testes unitários em test_services_pedido.py usando só
os Fakes, e adicionei a fixture fake_pedido_repository no conftest.py. No
flask_app.py, criei os endpoints POST /pedidos, POST /pedidos/<id>/confirmacao e
POST /pedidos/<id>/cancelamento e o helper _ler_booleano(). Escrevi os testes
e2e em test_pedido_api.py, cobrindo criação, id repetido, ticket sem anúncio ou
inexistente, campos faltando ou inválidos, pagamento aprovado e recusado,
confirmação de pedido já confirmado ou cancelado e cancelamento repetido.

**Arquivos:** src/rocketicket/service_layer/services.py,
src/rocketicket/entrypoints/flask_app.py, tests/conftest.py,
tests/unit/test_services_pedido.py, tests/e2e/test_pedido_api.py

**Decisões:**
- O valor do pedido vem do preço do anúncio ativo do ticket, buscado com
  get_ativa_por_ticket(), e não do JSON. É o mesmo motivo do valor_original no
  criar_anuncio: o comprador não pode escolher quanto vai pagar. Se o ticket não
  tiver anúncio ativo, o service lança RecursoNaoEncontrado (404).
- Ainda não há integração com um meio de pagamento, então o confirmar_pedido
  recebe pagamento_aprovado (true ou false), que simula essa resposta. Se for
  aprovado, o pagamento é aprovado e o pedido confirmado no mesmo commit; se o
  ticket não estiver ANUNCIADO, o Pedido lança TicketIndisponivel e nada é
  salvo, então dá para tentar de novo. Se for recusado, a recusa é salva e o
  pedido continua ABERTO, mas não pode mais ser confirmado, só cancelado. A API
  responde 200 nos dois casos, informando o resultado do pagamento, porque uma
  recusa não é erro da requisição.
- Na Fase 1, o service só lê o status do ticket e passa para o Pedido na
  confirmação. Vender o ticket e concluir a venda fica para a Fase 2, pelo
  evento PedidoConfirmado. Limitação conhecida até lá: depois de um pedido
  confirmado, o ticket continua ANUNCIADO, e um segundo pedido do mesmo ticket
  também pode ser confirmado.
- Id de pedido repetido lança PedidoJaExiste (409); pedido ou ticket inexistente
  lança RecursoNaoEncontrado (404); as violações do domínio (PedidoEncerrado,
  PagamentoJaProcessado e TicketIndisponivel) viram 400 pelo tratamento central
  de erros, sem try/except nas rotas. As rotas de ação seguem o formato
  /pedidos/<id>/confirmacao e /pedidos/<id>/cancelamento, o mesmo de
  /anuncios/<id>/cancelamento.
- pagamento_aprovado precisa ser um booleano do JSON. Valores como "true", 1 ou
  null são recusados com 400, para que nada ambíguo seja tratado como aprovação.

---

# Parte 2 — Fase 2

## fase2-checkpoint-1 — Arquitetura e ADRs

### Lucas Esteves (@LucasEsteves29)

**O que fiz:** criei os esqueletos do checkpoint 1: o docs/arquitetura.md com as
seis seções e o responsável de cada uma, e o docs/adr/template.md com a numeração
reservada dos ADRs. Escrevi o ADR 0001, que registra a decisão do mapeamento ORM
imperativo, as alternativas descartadas e as consequências.

**Arquivos:** docs/arquitetura.md, docs/adr/template.md,
docs/adr/0001-mapeamento-orm-imperativo.md

**Commits:** ccecc85 (esqueletos do arquitetura.md e do template de ADR)

**Decisão:**
- No ADR 0001, registrei as consequências negativas junto com as positivas,
  inclusive a de que a leitura do banco não passa pelo __init__, o que expôs o
  bug do teto de 110%. Mesmo com esses custos, a decisão continua aceita: o
  domínio puro é o que permite testar as regras de negócio sem banco.
- Cada seção do arquitetura.md traz, num comentário HTML, o que o enunciado exige
  e quem é o responsável, para cada integrante saber o que entregar sem precisar
  voltar ao enunciado.
### Miguel Duque (@miguelduq)

**O que fiz:** escrevi a seção 5 do docs/arquitetura.md, com a arquitetura
alternativa (Flask com Active Record), o diagrama em Mermaid comparando as duas,
a tabela por atributo de qualidade e a conclusão. Escrevi também o ADR 0004, que
registra a decisão da Fase 1 de criar a AbstractVendaRepository com
get_ativa_por_ticket() em vez de colocar a consulta na AbstractRepository
genérica.

**Arquivos:** docs/arquitetura.md, docs/adr/0004-consulta-extra-em-abstracao-propria.md

**Commits:** 3e42127

**Decisão:** escolhi o Active Record como alternativa, e não CQRS ou eventos,
porque é a alternativa mais simples que um grupo realmente usaria com Flask, e
ela ataca exatamente o que a nossa arquitetura tem de mais caro (repositórios,
Fakes e mapeamento separado). Assim a comparação mede o custo das camadas contra
o que elas protegem: as regras da Venda e do Pedido.

**Uso de IA:** usei o Claude (Anthropic) como assistente neste checkpoint. Ele
leu o repositório (código, histórico de commits e o esqueleto do arquitetura.md)
e redigiu um primeiro rascunho do ADR 0004 e da seção 5 a partir das decisões
que eu tinha tomado na Fase 1. Eu revisei o texto, conferi os hashes e as
afirmações sobre o código e ajustei o que não correspondia ao que fiz. A
responsabilidade pelo conteúdo é minha.

---

## fase2-checkpoint-2 — SOLID

### Caio Jose Carneiro (@caiojosesouz-dotcom)

**Entrega:** no C1, os commits `8d7e4d1` e `e907303` documentaram a violação de DIP
na rota de Ticket a partir do código de `f85f2d4` (29/09/2026). No C2, o commit
`ed6a19a` (03/11/2026) adicionou `ticket_repository_factory` à `create_app()` e
substituiu a instanciação direta de `SqlAlchemyTicketRepository` nos endpoints de
emissão, anúncio e confirmação de pedido. A seção "Depois" em `docs/solid.md`
registra a mudança, os testes, o custo e o limite da refatoração.

**Decisão:** manter SQLAlchemy como padrão na composição para preservar os chamadores
existentes e receber uma fábrica que devolve `AbstractRepository[Ticket]`. Ela recebe
a sessão da própria requisição. O service continua fazendo commit e o teardown continua
fechando a sessão. Os repositórios de outros agregados e o mapeamento ORM não foram
generalizados nesta entrega.

**Validação:** 235 testes passaram com Python 3.12: os 231 existentes e quatro novos
em `tests/integration/test_ticket_repository_injection.py`. Os novos cenários cobrem
emissão com fake sem banco, duplicidade, entrada inválida, ciclo de vida da sessão e
o fluxo de compra usando a fábrica nas três rotas que acessam Ticket.

**Uso de IA:** o Codex (OpenAI) auxiliou na análise do histórico, na implementação
da injeção, na escrita dos testes, na execução da suíte e na redação da documentação.

### Lucas Esteves (@LucasEsteves29)

**O que fiz:** criei o docs/solid.md com a introdução do checkpoint e uma seção por
integrante (Lucas, Caio, Igor, Miguel e Guilherme), cada uma com as partes "Antes" e
"Depois" e um comentário com o que o enunciado exige em cada parte. Preenchi o "Antes" da
minha seção, sobre o SRP no flask_app.py, usando o código do commit f85f2d4 (29/09). Nesse
commit, o create_app() e o módulo acumulam quatro responsabilidades: montar o app e a sessão
por requisição, traduzir exceções em códigos HTTP, validar e converter a entrada JSON
(_ler_json, _ler_texto e _ler_decimal) e declarar as rotas de todos os agregados. Como
evidência do problema, usei o histórico do arquivo: f85f2d4 (Lucas), e17c50a e 19cc75c
(Igor) e 835565f (Guilherme) mexeram no mesmo arquivo por motivos diferentes, e o
_ler_decimal e os tratadores de erro são compartilhados pelas rotas de mais de um agregado.
Essa primeira etapa foi só de documentação, sem alterar código.

Na segunda etapa, fiz a refatoração. Extraí a leitura e a validação do JSON para
entrypoints/entrada.py (ler_json, ler_texto, ler_booleano e ler_decimal) e a tradução de
exceções em respostas HTTP para entrypoints/erros.py (registrar_tratamento_de_erros(app)),
com os mesmos códigos e o mesmo corpo {"erro": ...}. A create_app() continua montando o app e
a sessão por requisição e chama essa função, e as rotas continuam no flask_app.py, que caiu de
141 para 98 linhas. Nas rotas de Venda e de Pedido, só troquei o nome das funções de leitura
chamadas. Escrevi 41 testes unitários em tests/unit/test_entrada.py e preenchi o "Depois" da
minha seção no docs/solid.md.

**Arquivos:** docs/solid.md, DECISIONS.md, src/rocketicket/entrypoints/flask_app.py,
src/rocketicket/entrypoints/entrada.py, src/rocketicket/entrypoints/erros.py,
tests/unit/test_entrada.py

**Commits:** f85f2d4 (29/09, anterior a 06/10), que é o código "antes" usado no
docs/solid.md. O hash deste commit de documentação entra aqui no commit da refatoração,
porque um commit não consegue registrar o próprio hash.

**Decisão:**
- Usei como "antes" o f85f2d4, meu próprio commit de 29/09, e não o estado atual do
  arquivo. A violação já está nele: a create_app() junta a sessão por requisição, os
  tratadores de erro e as rotas, o módulo ainda guarda os helpers de leitura, e a função
  reserva com comentários o lugar das rotas de Venda e de Pedido. Assim, o código criticado
  é do meu módulo, e os commits seguintes do Igor (e17c50a e 19cc75c) e do Guilherme
  (835565f) servem como evidência do problema, e não como código a corrigir.
- O problema concreto se apoia só em dados do repositório (git log, git show --numstat,
  git blame e git grep), com o comando citado ao lado de cada número, para que qualquer um
  possa conferir. Como o histórico não mostra conflito de merge no arquivo, escrevi "risco
  de conflito", e não que um conflito aconteceu.
- Registrei o "antes" num commit só de documentação, sem mexer no código, com a suíte em
  180 testes verdes. Depois disso, as refatorações do Igor e do Guilherme somaram 4 testes,
  então a referência do "Depois" é 184. Esses 184 passaram sem nenhuma alteração, e a suíte
  foi para 225 com os 41 testes novos: é essa a evidência de que o comportamento não mudou.
- Movi a validação e os tratadores de erro sem mudar nenhuma regra. Mudar uma regra junto com
  a refatoração tiraria da suíte o papel de evidência.
- Não reorganizei as rotas nem criei blueprints. As de Venda e de Pedido são de outros
  integrantes, e nelas mudei só o nome das funções chamadas (5 linhas do Igor e 6 do
  Guilherme). O custo é que a create_app() continua declarando as rotas dos três agregados,
  o que registrei no docs/solid.md como o que a refatoração não resolve.
- registrar_tratamento_de_erros(app) recebe o app para os tratadores continuarem valendo
  para todas as rotas, inclusive as que os testes e2e registram direto no app.
- Os testes de entrada.py não sobem o app. Só o ler_json precisa do request do Flask, e roda
  no contexto de requisição de um Flask vazio. Com a validação fora do flask_app.py, esses
  testes não carregam mais o SQLAlchemy.

**Uso de IA:** usei o Claude, como assistente nesta etapa
do checkpoint. Ele leu o repositório (código, testes, documentação e histórico de commits),
rodou os comandos de git citados no docs/solid.md e o pytest tests, e redigiu um primeiro
rascunho do esqueleto do docs/solid.md, da parte "Antes" da minha seção. Eu revisei o
texto, conferi os hashes, os números e as afirmações sobre o código e ajustei o que não
correspondia ao que fiz.


### Igor Leal (@igorbleal)

**O que fiz:** na primeira etapa deste checkpoint, preenchi o "Antes" da minha seção no
docs/solid.md, sobre a violação do Princípio da Responsabilidade Única (SRP) na classe
Venda em domain/model.py, usando o código do commit 331685a (24/09). Nesse commit, a
entidade Venda acumula duas responsabilidades com motivos de mudança distintos: controlar
o ciclo de vida e a identidade do anúncio (`__init__`, alterar_preco, cancelar, concluir e
_exigir_ativa) e calcular e validar a política financeira do teto de revenda de 110%
(_validar_preco com quantize e ROUND_DOWN). Como evidência do problema concreto, levantei
o histórico do bloco da Venda em model.py: cdd0311 e 331685a (Igor), 0a468e7 (Miguel) e
186b52c (Lucas) editaram a mesma classe, e a mudança na regra de arredondamento em 331685a
deixou alterar_preco() temporariamente divergente do `__init__()` até a correção em
186b52c. Na segunda etapa, realizei a refatoração extraindo o cálculo e a validação do
teto para a classe PoliticaTetoPercentual em domain/model.py (com os métodos
calcular_limite() e validar()), atualizei Venda e o caso de uso criar_anuncio em
service_layer/services.py para delegarem a validação à política de preço, adicionei os
testes unitários em tests/unit/test_venda.py e tests/unit/test_services_venda.py e
preenchi a seção "Depois" no docs/solid.md.

**Arquivos:** docs/solid.md, src/rocketicket/domain/model.py,
src/rocketicket/service_layer/services.py, tests/unit/test_venda.py,
tests/unit/test_services_venda.py, DECISIONS.md

**Commits:** 331685a (24/09, anterior a 06/10, código "antes" da Venda usado no
docs/solid.md), 91ce98f (01/11, rascunho inicial da seção "Antes"), fd6e50d, 81ff350,
cad3eef e adf83e5 (02/11, documentação do "Antes" no docs/solid.md e no DECISIONS.md) e
576af01 (03/11, refatoração extraindo PoliticaTetoPercentual e testes
unitários).

**Decisão:**
- Usei como "antes" o commit 331685a (24/09), de minha autoria, porque ele registra o
  momento exato em que a mudança na regra financeira do teto de 110% obrigou a editar a
  classe Venda e expôs a duplicação com alterar_preco(), corrigida depois em 186b52c.
- Apoiei o problema concreto em dados verificáveis do repositório (git log,
  git show --numstat, git blame -L 156,241 e git grep), citando os comandos junto aos
  números no docs/solid.md para manter o mesmo padrão de evidência do documento.
- Mantive o primeiro commit restrito à documentação, sem tocar em src/ ou tests/, servindo
  de linha de base para a refatoração do segundo commit.
- Na refatoração, declarei politica_preco = PoliticaTetoPercentual() também como atributo
  de classe em Venda, além do parâmetro opcional no `__init__()`. Como o mapeamento
  imperativo do SQLAlchemy (adapters/orm.py) reconstrói entidades carregadas do banco sem
  chamar `__init__()`, o atributo de classe garante que chamar alterar_preco() em uma Venda
  vinda da sessão continue funcionando sem exigir novas colunas na tabela vendas.
- Mantive PoliticaTetoPercentual() (110%) como valor padrão tanto em Venda quanto em
  criar_anuncio para que toda a suíte existente continuasse passando sem alterações, e
  acrescentei 3 testes novos exercitando o cálculo isolado do limite e uma política sem
  ágio (100%).

**Uso de IA:** usei o Antigravity (Google Gemini) como assistente nas duas etapas do checkpoint. 
Na primeira, ele levantou o histórico de git de model.py e services.py e redigiu o rascunho do 
“Antes”. Na segunda, ajudou a estruturar a extração da PoliticaTetoPercentual preservando a 
compatibilidade com o mapeamento do SQLAlchemy, sugeriu os testes unitários e redigiu o rascunho
 do “Depois”. Eu revisei o código e o texto, executei a suíte com pytest e conferi hashes, linhas 
 e afirmações. A responsabilidade pelo conteúdo é minha.


### Miguel Duque (@miguelduq)

**O que fiz:** na primeira etapa, preenchi o "Antes" da minha seção no docs/solid.md,
sobre uma violação do Princípio da Segregação de Interfaces (ISP) no repositório da Venda.
A AbstractVendaRepository, que criei em 73b9847 e implementei em 54e16d6 (28/09), junta
add(), get() e get_ativa_por_ticket(), e o criar_pedido (ec01929, 29/09) recebe essa
interface inteira para usar só a consulta da venda ativa. Mostrei três efeitos: o service do
Pedido ganha acesso de escrita à Venda, uma fonte só de leitura (cache ou réplica) teria de
implementar um add() que lança erro, violando também o LSP, e os testes do Pedido não
conseguem usar um dublê mínimo. Na segunda etapa, fiz a refatoração: criei a interface
ConsultaVendaAtiva, só com get_ativa_por_ticket(), fiz a AbstractVendaRepository herdar dela
e troquei o tipo do repo_vendas no criar_pedido. Escrevi tests/unit/test_consulta_venda_ativa.py,
com 6 testes, e preenchi o "Depois" no docs/solid.md.

**Arquivos:** docs/solid.md, src/rocketicket/adapters/repository.py,
src/rocketicket/service_layer/services.py, tests/unit/test_consulta_venda_ativa.py,
DECISIONS.md

**Commits:** 73b9847 e 54e16d6 (28/09, anteriores a 06/10, código "antes"), adf2561
(02/11, seção "Antes"), da058ef (03/11, refatoração e testes) e o commit deste registro
(03/11, seção "Depois" e DECISIONS.md).

**Decisão:** em vez de criar um repositório separado para o Pedido, fiz a
AbstractVendaRepository herdar da nova ConsultaVendaAtiva. Assim o SqlAlchemyVendaRepository
e o FakeVendaRepository continuaram iguais, nenhum teste existente precisou mudar e a
refatoração ficou restrita a uma classe abstrata nova e a uma anotação de tipo.

**Uso de IA:** usei o Claude (Anthropic) como assistente nas duas etapas deste
checkpoint. Ele analisou o histórico do repositório, identificou a violação de ISP no
repositório da Venda, redigiu as seções "Antes" e "Depois" do docs/solid.md, escrevemos juntos a
interface ConsultaVendaAtiva, a mudança no criar_pedido e os testes de
test_consulta_venda_ativa.py, e me ajudou a resolver conflito do docs/solid.md no merge com a main.
Eu rodei a suíte de testes na minha máquina, revisei o código e o texto e fiz os commits.
A responsabilidade pelo conteúdo é minha.
