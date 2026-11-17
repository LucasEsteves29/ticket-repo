# Retrospectiva da Fase 2

A pergunta da retrospectiva é se, depois de conviver com esta arquitetura, refatorar o
código e aplicar padrões, nós a escolheríamos de novo. A resposta curta é sim, com dois
ajustes. Este documento revisita a análise do checkpoint 1, mostra o que a Fase 2 revelou e
justifica a decisão. Os números vêm do repositório, no commit `f6b59e4`, e os detalhes de
cada mudança estão no `solid.md`, no `gof.md` e na seção 6 do `arquitetura.md`.

Não implementamos o caso de uso opcional em `experimentos/`. A comparação com o estilo
alternativo se apoia na análise da seção 5 do `arquitetura.md` e nas medidas abaixo.

## 1. Previsões do checkpoint 1

A análise feita no checkpoint 1 está na seção 5 do `arquitetura.md` (commit `a753e66`, de
22/10): ela comparou a arquitetura atual com Flask + Active Record pelos quatro atributos e
concluiu que manteria a atual. As previsões, uma a uma:

| Atributo | Previsão (seção 5.2) | O que aconteceu | Confirmou? |
|---|---|---|---|
| **Testabilidade** | A atual ganha: domínio puro e services testados com Fakes, sem banco | A suíte foi de 180 para 336 testes ao longo da Fase 2, e os 223 unitários rodam em menos de 1 segundo sem carregar o SQLAlchemy | Sim |
| **Modificabilidade** | Depende: a atual ganha em mudança de infraestrutura e perde em caso de uso novo, que atravessa as camadas | As 4 mudanças de infraestrutura (SRP do `flask_app.py`, ISP, DIP e Decorator) não tocaram o `model.py`. O Memento e o Adapter, que acrescentaram funcionalidade, alteraram 5 e 6 arquivos de `src/` | Sim, nos dois sentidos |
| **Corretude das regras** | A atual ganha: as invariantes só mudam pela raiz, e o service decide a ordem das operações | Valeu dentro de cada agregado. Entre agregados, não: um pedido confirmado não vende o ticket, e um segundo pedido do mesmo ticket também é confirmado (seção 4.1 do `arquitetura.md`) | Em parte |
| **Simplicidade** | O Active Record ganha: a atual tem mais arquivos e indireção | `adapters/` passou a ter 578 linhas, contra 534 do domínio, e cada padrão GoF acrescentou classes | Sim |

A previsão que falhou é a mais importante. A conclusão do checkpoint 1 citava, como
argumento a favor da arquitetura, "o pedido que só confirma com pagamento aprovado e ticket
ainda anunciado". A regra está certa dentro do `Pedido`, mas o `confirmar_pedido` lê o
status do ticket e não o altera: depois da confirmação, o ticket continua `ANUNCIADO` e a
venda continua `ATIVA`. Reproduzimos pela API em `f6b59e4`: dois pedidos de compradores
diferentes para o mesmo ticket terminaram ambos `confirmado`, com o ticket ainda
`anunciado` e no nome do vendedor, e a venda ainda `ativa`. A docstring do service deixa isso "para os eventos da Fase 2", e
esse tema saiu do trabalho. As camadas não impediram a falha: o domínio puro protege as
regras de cada agregado, mas a regra que cruza três agregados depende de o service lembrar
de fazer todas as etapas.

### Trade-offs que pesaram mais na prática

1. **O SQLAlchemy recria os objetos sem chamar o `__init__`.** A análise do checkpoint 1
   não previu esse custo, e foi o que mais apareceu. Ele causou o bug do teto de 110%,
   corrigido com o arredondamento para baixo (ADR 0003), e obrigou dois padrões a se
   adaptarem: o State deriva o estado do `status` (`_ESTADOS`), e o Observer cria a lista de
   observadores sob demanda (`Venda._observadores()`). É o preço do mapeamento imperativo
   (ADR 0001), que por outro lado é o que mantém o domínio puro.
2. **O `create_app()` como ponto de composição.** A SRP reduziu o `flask_app.py` de 141 para
   98 linhas, mas o DIP, o Decorator, o Memento e o Adapter o levaram de volta a 153. Toda
   mudança que acrescenta uma rota ou uma dependência passa por esse arquivo, que concentra
   os três agregados.
3. **Três lugares por consulta nova.** A previsão do ADR 0004 se confirmou: cada consulta
   nova da Venda exige a abstração, a implementação real e o Fake. Foi aceitável porque a
   Fase 2 acrescentou poucas consultas, mas é um custo que cresce com o sistema.

## 2. Evidências da Fase 2

A pergunta é se as camadas facilitaram ou atrapalharam as refatorações e os padrões. A
melhor medida é quanto cada mudança precisou mexer nos testes que já existiam: se o teste
antigo continua valendo sem alteração, a mudança não quebrou o comportamento, e a camada
isolou a mudança. Contamos as linhas removidas de arquivos de teste em cada commit
(`git show --numstat -- tests`):

| Commit | Mudança | Linhas removidas de testes existentes |
|---|---|---|
| `17af148` | SRP no `flask_app.py` | 0 |
| `ed6a19a` | DIP nas rotas do Ticket | 0 |
| `576af01` | SRP na Venda | 1 |
| `da058ef` | ISP na consulta da venda ativa | 0 |
| `50077c9` | OCP na confirmação do Pedido | 0 |
| `a4f0292` | State no Ticket | 0 |
| `7435b36` | Memento no preço do anúncio | 0 |
| `b48915a` | Decorator na auditoria de check-in | 2 |
| `32cf2cf` | Observer na Venda | 0 |
| `e10e80b` | Adapter no gateway de pagamento | 42 |

**Onde as camadas facilitaram.** Em nove das dez mudanças, os testes existentes ficaram
praticamente intactos (no máximo duas linhas removidas), e todas acrescentaram testes novos.
Duas situações mostram o mecanismo:

- *Refatorar sem medo.* No State, escrevemos uma matriz de caracterização com as 16
  combinações de status e operação, rodamos contra o código antigo e só então refatoramos. Os
  testes existentes passaram sem alteração (`gof.md`). Na SRP do `flask_app.py`, os 184
  testes anteriores passaram sem mudança, incluindo os e2e de todos os agregados (`solid.md`).
  Isso só é barato porque os testes unitários não precisam de banco.
- *Trocar infraestrutura sem tocar o domínio.* O DIP e o Decorator mudaram a forma de obter
  e de auditar o repositório do Ticket, e o `model.py` não teve nenhuma linha alterada.
  As portas abstratas (`AbstractTicketRepository`) deram o lugar exato para encaixar a
  mudança.

**Onde as camadas atrapalharam.** O Adapter foi a exceção: ele mudou o contrato da API (a
confirmação passou a exigir um `token_pagamento`), e isso alterou os testes e2e do Pedido e
uma linha do teste de injeção do Caio. A arquitetura não tem culpa da mudança de contrato,
mas ela atravessou todas as camadas: domínio, service, adaptador, rota e testes de cada
nível, em 6 arquivos de `src/`. O Memento passou pelo mesmo caminho (5 arquivos de `src/`
para dois casos de uso e uma tabela). Funcionalidade nova, nesta arquitetura, é cara.

O balanço é que as camadas cumpriram o que prometiam para o que mais fizemos na Fase 2, que
foi refatorar e trocar infraestrutura, e cobraram o preço previsto quando acrescentamos
funcionalidade.

## 3. Decisão final

**Manteríamos a arquitetura atual**, coerente com a conclusão da seção 5.3 do
`arquitetura.md`, mas com dois ajustes que a Fase 2 mostrou serem necessários.

O motivo para manter é o mesmo do checkpoint 1, agora com evidência: as regras que valem
dinheiro (o teto de 110%, o anúncio único por ticket, a confirmação só com pagamento
aprovado) ficaram protegidas dentro dos agregados durante dez mudanças de cinco pessoas, e a
suíte unitária rápida e sem banco foi o que permitiu fazer essas mudanças com segurança. No
Active Record, essas garantias dependeriam de disciplina, porque qualquer rota pode alterar
um atributo e salvar.

Os dois ajustes:

1. **Coordenar no service as regras que cruzam agregados.** O `confirmar_pedido` deve, na
   mesma transação, vender o ticket (`ticket.vender()`) e concluir a venda
   (`venda.concluir()`). A `Session` do SQLAlchemy já grava tudo num único commit (Unit of
   Work, seção 3.2 do `frameworks.md`), então isso não exige o mecanismo de eventos que saiu
   do trabalho, só um service que faça todas as etapas. É a correção do risco da seção 4.1.
2. **Separar as rotas por agregado.** As rotas de Ticket, Venda e Pedido iriam para módulos
   próprios em `entrypoints/` (por exemplo, com *blueprints* do Flask), e o `create_app()`
   ficaria só com a composição das dependências. É a parte da SRP que ficou em aberto no
   `solid.md` e o risco da seção 4.3.

A solução híbrida sugerida na seção 5.3 continua válida para o futuro: consultas que só leem
dados, como a listagem de anúncios ativos por evento, poderiam usar SQL direto, sem passar
por repositórios e agregados. Como o RocketTicket ainda não tem essas consultas, não há o que
mudar hoje.