# Padrões GoF no RocketTicket

## Lucas — State

### Nome e categoria

**State**, padrão comportamental do GoF. A intenção, nos termos do catálogo, é permitir que
um objeto altere o seu comportamento quando o seu estado interno muda, como se tivesse
mudado de classe. No RocketTicket, o objeto é o `Ticket`, e o estado interno é o `status`.

### Contexto e problema

O `Ticket` tem quatro status (`DISPONIVEL`, `ANUNCIADO`, `VENDIDO` e `USADO`) e quatro
métodos cujo resultado depende deles: `anunciar()`, `retirar_anuncio()`, `vender()` e
`usar()`. Antes do State, cada método decidia o que era permitido com uma cadeia de `if`
sobre `self.status`: eram 9 comparações de status nos quatro métodos, mais a regra do
próprio dono em `vender()`. Este é o `usar()` em `513bc0a`, o commit anterior a `a4f0292`
(docstring omitida):

```python
def usar(self) -> None:
    if self.status is StatusTicket.USADO:
        raise TicketJaUsado(f"ticket {self.id} já foi usado")
    if self.status is StatusTicket.ANUNCIADO:
        raise TicketAnunciado(
            f"ticket {self.id} está anunciado e não pode ser usado"
        )
    if self.status is not StatusTicket.VENDIDO:
        raise TicketNaoVendido(
            f"ticket {self.id} não foi vendido (status: {self.status.value})"
        )
    self.status = StatusTicket.USADO
```

O comportamento de cada status ficava espalhado pelos quatro métodos, misturado ao de todos
os outros. Um estado novo, como reintroduzir `DISPONIVEL` como o status da venda primária,
obrigava a editar os quatro. A ordem das checagens também importava: em `vender()`, `USADO`
precisava ser testado antes de "não anunciado", porque um ticket usado satisfaz as duas
condições, e é a ordem que decide qual exceção sai. O próprio `DISPONIVEL`, que nenhum
caminho alcança, tinha um comportamento que ninguém escreveu de propósito: era o que sobrava
depois de passar por todos os `if`.

Depois de `a4f0292`, o Ticket só delega, e cada status responde por si (as partes omitidas
estão marcadas com `# (...)`):

```python
class Ticket:
    # (...)
    @property
    def _estado(self) -> EstadoTicket:
        return _ESTADOS[self.status]

    def usar(self) -> None:
        self._estado.usar(self)


class Anunciado(EstadoTicket):
    # (...)
    def usar(self, ticket: "Ticket") -> None:
        raise TicketAnunciado(f"ticket {ticket.id} está anunciado e não pode ser usado")


class Vendido(EstadoTicket):
    def usar(self, ticket: "Ticket") -> None:
        ticket.status = StatusTicket.USADO
```

### Alternativa considerada

- **Manter os `if`.** É o código mais curto e deixa o fluxo de cada método num lugar só.
  Foi descartado pelo problema acima: cada status novo, ou cada mudança na regra de um
  status, continuaria passando pelos quatro métodos e pela ordem das checagens.
- **Uma tabela de transições** `(status, método) -> status de destino`, como
  `{(VENDIDO, "anunciar"): ANUNCIADO, ...}`. Ela descreve bem as 5 transições válidas da
  matriz de caracterização, mas não basta para as outras 11 posições, que são recusas: cada
  par inválido lança uma exceção diferente, com mensagem própria. São 5 classes de exceção e
  9 mensagens distintas, e só a `TicketJaUsado` tem uma mensagem por método. Além disso, o
  `vender()` tem uma regra que não depende só do status, a de não vender ao próprio dono
  (`CompraDoProprioTicket`), checada depois do status. A transição do `vender()` também
  troca o dono, o que uma tabela de status não representa. Para cobrir tudo isso, cada célula
  teria de guardar uma função, e a tabela viraria o State sem nomes.
- **Uma subclasse de `Ticket` por estado.** Descartada porque o ORM mapeia uma única classe:
  o `orm.py` faz `map_imperatively(model.Ticket, tickets)`. Com subclasses, cada transição
  exigiria trocar a classe do objeto, e o mapeamento teria de virar herança polimórfica, com
  o `status` como discriminador. Isso levaria para o `adapters/orm.py` uma decisão de
  comportamento do domínio. No State, a classe mapeada continua uma só, e o que muda é o
  objeto para o qual ela delega.

### Participantes (classes reais)

| Papel no GoF | No código (`domain/model.py`) | O que faz |
|---|---|---|
| Context | `Ticket` | guarda os dados e o `status`; `anunciar()`, `retirar_anuncio()`, `vender()` e `usar()` só delegam ao estado atual, passando o próprio ticket |
| State | `EstadoTicket` | declara os quatro métodos, todos recebendo o ticket, com o comportamento padrão: `anunciar()` passa para `ANUNCIADO`, `retirar_anuncio()` e `vender()` lançam `TicketNaoAnunciado`, e `usar()` lança `TicketNaoVendido` |
| ConcreteState | `Disponivel`, `Anunciado`, `Vendido` e `Usado` | cada um sobrescreve só o que muda no seu status: `Disponivel` não sobrescreve nada, `Vendido` sobrescreve só `usar()`, e `Anunciado` e `Usado` sobrescrevem os quatro |
| (escolha do estado) | `_ESTADOS` e a propriedade `Ticket._estado` | `_ESTADOS` liga cada `StatusTicket` à instância do seu estado, e `_estado` devolve `_ESTADOS[self.status]` |

**Por que o estado é derivado do `status`.** No GoF, o Context guarda uma referência ao
objeto State e a troca a cada transição. Aqui o Ticket não guarda o estado: o `status` é a
única fonte de verdade, e o `_estado` é recalculado a cada chamada. O motivo é o mapeamento
imperativo (ADR 0001): a coluna persistida é `status`, e o SQLAlchemy recria o Ticket lido do
banco sem chamar `__init__`. Um atributo de estado criado no `__init__` não existiria nos
tickets carregados, e recriá-lo exigiria um gancho do ORM, que o `model.py` não pode conhecer.

Esse desenho tem duas consequências:

- **Quem faz a transição é o ConcreteState.** `Anunciado.vender()` troca `ticket.dono_id` e
  `ticket.status`. Como o estado vem do status, mudar o status já troca o estado.
- **Os estados são compartilhados.** Eles não guardam nada e recebem o ticket como
  parâmetro, então uma instância de cada, no `_ESTADOS`, serve para todos os tickets. O GoF
  prevê esse compartilhamento quando o estado não tem dados próprios.

### Diagrama de classes (Mermaid)

```mermaid
classDiagram
    class Ticket {
        +id: str
        +evento_id: str
        +valor_original: Decimal
        +dono_id: str
        +status: StatusTicket
        -_estado: EstadoTicket
        +anunciar()
        +retirar_anuncio()
        +vender(novo_dono_id: str)
        +usar()
    }

    class EstadoTicket {
        +anunciar(ticket: Ticket)
        +retirar_anuncio(ticket: Ticket)
        +vender(ticket: Ticket, novo_dono_id: str)
        +usar(ticket: Ticket)
        -_nao_anunciado(ticket: Ticket) TicketNaoAnunciado
    }

    class Disponivel

    class Anunciado {
        +anunciar(ticket: Ticket)
        +retirar_anuncio(ticket: Ticket)
        +vender(ticket: Ticket, novo_dono_id: str)
        +usar(ticket: Ticket)
    }

    class Vendido {
        +usar(ticket: Ticket)
    }

    class Usado {
        +anunciar(ticket: Ticket)
        +retirar_anuncio(ticket: Ticket)
        +vender(ticket: Ticket, novo_dono_id: str)
        +usar(ticket: Ticket)
    }

    class ESTADOS["_ESTADOS"] {
        <<dict>>
        DISPONIVEL: Disponivel
        ANUNCIADO: Anunciado
        VENDIDO: Vendido
        USADO: Usado
    }

    EstadoTicket <|-- Disponivel
    EstadoTicket <|-- Anunciado
    EstadoTicket <|-- Vendido
    EstadoTicket <|-- Usado
    Ticket ..> ESTADOS : _estado busca pelo status
    ESTADOS o-- EstadoTicket : uma instância por status
    Ticket ..> EstadoTicket : delega os 4 métodos
    EstadoTicket ..> Ticket : altera status e dono_id
```

### Teste

O `tests/unit/test_ticket_estados.py` é a matriz de caracterização. Para cada um dos 16 pares
(4 status × 4 métodos), ele monta o ticket naquele status, chama o método e confere a
transição (status e dono finais) ou a exceção, com a mensagem exata. Nas recusas, confere
também que o ticket não mudou. Dos 16 pares, 5 são transições e 11 são recusas. O arquivo
tem 21 testes:

| Testes | O que conferem |
|---|---|
| 16 `test_matriz` | os 16 pares, um por status em cada método (`TestAnunciar`, `TestRetirarAnuncio`, `TestVender` e `TestUsar`) |
| 1 `test_cobre_todos_os_status_em_cada_metodo` | falha se algum status ficar fora da matriz em algum método |
| 1 `test_vender_ao_proprio_dono_falha` | a `CompraDoProprioTicket`, com a mensagem exata, num ticket anunciado |
| 3 `test_status_tem_prioridade_sobre_a_regra_do_proprio_dono` | fora de `ANUNCIADO`, a checagem de status vem antes da regra do próprio dono |

Os tickets são montados pela API do domínio, menos o de `DISPONIVEL`: como nenhum caminho
alcança esse status, o helper `disponivel()` o atribui na mão, só para fixar o comportamento
que o código antigo tinha.

A matriz foi escrita e rodada antes da refatoração, contra o código com os `if`. Isso pode ser
conferido, porque o arquivo de `a4f0292` passa também contra o `model.py` de `a4f0292~1`. Os
comandos abaixo criam uma cópia do repositório nesse commit, trazem o teste de `a4f0292` e
rodam só ele, com o resultado `21 passed`:

```sh
git worktree add ../antes-do-state a4f0292~1
git -C ../antes-do-state checkout a4f0292 -- tests/unit/test_ticket_estados.py
pytest ../antes-do-state/tests/unit/test_ticket_estados.py
git worktree remove --force ../antes-do-state
```

A suíte existente passou sem nenhuma alteração. O `git show a4f0292 --stat` mostra que o
único arquivo de teste do commit é o novo:

```text
$ git show a4f0292 --stat
 DECISIONS.md                      |  46 +++++++
 docs/gof.md                       | 256 ++++++++++++++++++++++++++++++++++++++
 src/rocketicket/domain/model.py   | 137 ++++++++++++++------
 tests/unit/test_ticket_estados.py | 192 ++++++++++++++++++++++++++++
 4 files changed, 591 insertions(+), 40 deletions(-)

$ pytest tests    # em a4f0292^, antes do State
235 passed
$ pytest tests    # em a4f0292, com o State
256 passed
```

Os 256 são os 235 testes que já existiam, sem nenhuma mudança, mais os 21 da matriz.

### Custo

- **Mais classes e uma indireção para ler o fluxo.** São cinco classes e um dicionário a
  mais, e o `model.py` cresceu 57 linhas no commit (+97/−40). Para saber o que
  `ticket.vender()` faz, não basta ler o `Ticket`: é preciso abrir o `EstadoTicket.vender()`,
  que vale para dois status, e as versões de `Anunciado` e de `Usado`.
- **O estado vive separado do Ticket.** Os ConcreteStates escrevem `ticket.status` e
  `ticket.dono_id` de fora da classe, então as regras que mudam os dados do Ticket deixaram
  de morar só nele e se dividem entre cinco classes.
- **`DISPONIVEL` ganhou uma classe mesmo sendo inalcançável.** `Disponivel` existe para o
  `_ESTADOS` cobrir todos os status e para preservar o comportamento que o código antigo tinha
  para esse status.
- **O `anunciar()` padrão faz a transição.** Como no código antigo, um status que não
  sobrescreva `anunciar()` pode ser anunciado. Um status novo também precisa entrar no
  `_ESTADOS`, senão o `_estado` lança `KeyError`. O
  `test_cobre_todos_os_status_em_cada_metodo` obriga a pôr o status novo na matriz, onde as
  duas falhas aparecem.

**Por que compensa.** Um estado novo é uma classe nova e uma linha no `_ESTADOS`, sem tocar
nos métodos do Ticket, e mudar a regra de um status mexe só na classe dele. No exemplo do
contexto, reintroduzir `DISPONIVEL` como venda primária passa a ser editar a `Disponivel`, e
não os quatro métodos e a ordem de nove checagens. O ganho vale para estados novos, não para
operações novas: um método novo no Ticket, como um `reservar()`, ainda exige um método no
`EstadoTicket` e uma decisão em cada estado.

## Caio — Decorator

### Nome e categoria

<!--
Responsável: Caio
O enunciado exige: o nome do padrão e a sua categoria no GoF.
-->

### Contexto e problema

<!--
Responsável: Caio
O enunciado exige: o contexto e o problema real do domínio que o padrão resolve.
-->

### Alternativa considerada

<!--
Responsável: Caio
O enunciado exige: a alternativa considerada.
-->

### Participantes (classes reais)

<!--
Responsável: Caio
O enunciado exige: os participantes do padrão, mapeados para as classes reais do código.
-->

### Diagrama de classes (Mermaid)

<!--
Responsável: Caio
O enunciado exige: o diagrama de classes em Mermaid, com a fonte em texto neste arquivo.
-->

### Teste

<!--
Responsável: Caio
O enunciado exige: o teste que cobre o padrão.
-->

### Custo

<!--
Responsável: Caio
O enunciado exige: o custo de introduzir o padrão.
-->

## Igor — Memento

### Nome e categoria

**Memento**, padrão comportamental do GoF. A intenção, nos
termos do catálogo, é capturar e externalizar um estado interno de um objeto sem violar o
encapsulamento, para que o objeto possa ser restaurado para esse estado mais tarde. No
Rocketicket, o objeto (*Originator*) é a `Venda`, e o estado interno capturado é o `preco`
do anúncio.

### Contexto e problema

Uma Venda ativa permite que o vendedor reajuste o preço anunciado dentro do limite anti-cambismo
(`PoliticaTetoPercentual`, teto padrão de 110% sobre `valor_original` truncado em centavos com
`ROUND_DOWN`). Até `a4f0292`, o commit anterior a `7435b36`, alterar_preco() apenas validava o
novo valor e sobrescrevia `self.preco`.

```python
def alterar_preco(self, novo_preco: Decimal) -> None:
    self._exigir_ativa("ter o preço alterado")
    self._validar_preco(novo_preco)
    self.preco = novo_preco
```

Quando o vendedor errava a digitação ou desistia de uma promoção relâmpago — por exemplo, baixava
um ingresso de `R$ 108,00` para `R$ 95,00` e depois para `R$ 80,00` —, os valores anteriores se
perdiam. Para permitir desfazer alterações sucessivas em ordem LIFO (*Last-In, First-Out*), o
sistema precisa guardar os preços anteriores e restaurá-los mais tarde, respeitando três restrições
do domínio:

1. **Encapsulamento do histórico fora da `Venda`**: a `Venda` governa o ciclo de vida do anúncio
   (`ATIVA`, `CANCELADA`, `CONCLUIDA`) e a validação do teto de revenda; ela não deve gerenciar
   pilha de desfazer nem expor detalhes de armazenamento de snapshots para os clientes.
2. **Preservação das invariantes na restauração**: restaurar um preço não pode contornar as regras
   da `Venda`. Se o anúncio tiver sido encerrado (`CANCELADA` ou `CONCLUIDA`) entre a alteração e a
   tentativa de desfazer, a restauração deve falhar com `VendaEncerrada`. Se a `politica_preco` da
   venda tiver sido trocada por uma política mais restritiva, um preço antigo que hoje exceda o
   teto deve ser recusado com `PrecoAcimaDoLimite`. Além disso, um snapshot de uma venda não pode
   ser aplicado a outra (`MementoDeOutraVenda`).
3. **Persistência entre requisições HTTP**: como a API Flask é *stateless*, o *Caretaker* não pode
   ser apenas uma lista em memória local à função; os mementos precisam sobreviver entre o
   `PUT /anuncios/<venda_id>/preco` e os `POST /anuncios/<venda_id>/preco/desfazimento` seguintes.

Depois de `7435b36`, a `Venda` fotografa e restaura seu próprio preço por meio de
`MementoPrecoVenda`:

```python
class MementoPrecoVenda:
    def __init__(self, venda_id: str, preco: Decimal):
        self._venda_id = venda_id
        self._preco = preco

    @property
    def venda_id(self) -> str:
        return self._venda_id
```

```python
class Venda:
    # (...)
    def salvar_preco(self) -> MementoPrecoVenda:
        return MementoPrecoVenda(self.id, self.preco)

    def restaurar_preco(self, memento: MementoPrecoVenda) -> None:
        self._exigir_ativa("ter o preço restaurado")
        if memento.venda_id != self.id:
            raise MementoDeOutraVenda(
                f"o preço guardado é da venda {memento.venda_id}, não da venda {self.id}"
            )
        self._validar_preco(memento._preco)
        self.preco = memento._preco
```

### Alternativa considerada

- **Padrão Command com `Execute()` / `Unexecute()`** (ex.: objeto `ComandoAlterarPreco` guardando
  `venda_id`, `preco_anterior` e `novo_preco`): o catálogo GoF relaciona Command e Memento no
  desfazimento de operações, mas aqui há apenas uma operação reversível (a troca de preço) e nenhum
  requisito de fila de comandos, agendamento, macrocomandos ou *redo* polimórfico. Além disso,
  mesmo usando Command, o próprio GoF aponta que o comando ainda precisaria guardar o estado
  anterior da `Venda` para restaurá-lo sem expor mutação irrestrita — exatamente o papel do
  Memento. Criar uma hierarquia de comandos somada à persistência do estado anterior traria duas
  abstrações para resolver o problema de uma.
- **Atributo `preco_anterior: Decimal | None` ou lista `precos_anteriores: list[Decimal]` dentro de
  `Venda`**: um único campo `preco_anterior` permitiria apenas 1 nível de *undo* (um segundo reajuste
  sobrescreveria o primeiro valor); já embutir uma pilha de histórico dentro de `Venda` poluiria a
  entidade de domínio com estado de navegação de interface/aplicação, misturando o modelo do
  anúncio com a mecânica de armazenamento do histórico.
- **Enviar o preço antigo pelo cliente num novo `PUT /anuncios/<id>/preco`**: transfere para o
  cliente a responsabilidade de lembrar a pilha de preços anteriores e perde a garantia de que a
  operação restaura um preço que realmente esteve em vigor naquele anúncio.

### Participantes (classes reais)

| Papel no GoF | No código (`domain/model.py`, `adapters/repository.py`, `service_layer/services.py`) | O que faz |
| :--- | :--- | :--- |
| **Originator** | `Venda` (`src/rocketicket/domain/model.py`) | Cria um `MementoPrecoVenda` com o preço atual em `salvar_preco()` (*CreateMemento*) e restaura seu preço a partir dele em `restaurar_preco(memento)` (*SetMemento*), validando que a venda está `ATIVA`, que o memento pertence ao mesmo `self.id` e que o valor atende a `self._validar_preco()`. |
| **Memento** | `MementoPrecoVenda` (`src/rocketicket/domain/model.py`) | Guarda o snapshot do preço (`_venda_id` e `_preco`). Oferece interface estreita pública (`venda_id` via `@property` e `__repr__` sem expor o valor) para o *Caretaker* e interface larga (`_preco`) lida apenas por `Venda.restaurar_preco()`. |
| **Caretaker** | `AbstractHistoricoDePrecos`, `SqlAlchemyHistoricoDePrecos` (`src/rocketicket/adapters/repository.py`), `FakeHistoricoDePrecos` (`tests/conftest.py`) e os serviços `alterar_preco` / `desfazer_alteracao_de_preco` (`src/rocketicket/service_layer/services.py`) | `alterar_preco()` pede `venda.salvar_preco()` antes de aplicar o novo preço e empilha o memento em `historico.guardar(memento)`. `desfazer_alteracao_de_preco()` desempilha o último memento com `historico.desempilhar(venda_id)` (LIFO) e o entrega a `venda.restaurar_preco(memento)`, sem inspecionar nem modificar `_preco`. |

#### Interface estreita e interface larga em Python

O capítulo de Memento do GoF destaca que o padrão exige duas interfaces: uma **ampla** para o
*Originator* (que lê e grava o estado interno guardado) e uma **estreita** para o *Caretaker* (que
só armazena e transporta o memento como um objeto opaco). Em C++, isso é imposto com `friend class
Originator`. Em Python não existe a palavra-chave `friend`, então a fronteira é expressa pela
convenção de encapsulamento da linguagem:

- **Interface estreita (pública)**: `MementoPrecoVenda` expõe apenas a propriedade de leitura
  `venda_id` (para o *Caretaker* indexar a pilha por anúncio) e um `__repr__` que identifica a
  venda sem revelar o preço (`<MementoPrecoVenda da venda v-1>`). Não há propriedade pública `preco`
  nem método de mutação.
- **Interface larga (restrita ao Originator)**: o atributo `_preco` é privado por convenção e lido
  exclusivamente por `Venda.restaurar_preco()`. No adaptador ORM (`src/rocketicket/adapters/orm.py`),
  `_mapear_historico_precos()` liga explicitamente as colunas da tabela `historico_precos` (`id`,
  `venda_id`, `preco`) aos atributos privados `_id`, `_venda_id` e `_preco`, permitindo persistir o
  memento em SQLite sem abrir atributos públicos no domínio.

#### Guarda das invariantes na restauração

Diferente de um *setter* direto, `Venda.restaurar_preco(memento)` passa pelas mesmas barreiras de
domínio de `Venda.alterar_preco(novo_preco)`:

1. `self._exigir_ativa("ter o preço restaurado")` impede que uma venda já `CONCLUIDA` ou
   `CANCELADA` tenha seu preço alterado retroativamente (`VendaEncerrada`).
2. `if memento.venda_id != self.id` impede que um memento de outra venda seja aplicado por engano
   (`MementoDeOutraVenda`).
3. `self._validar_preco(memento._preco)` revalida o preço restaurado contra a `politica_preco`
   vigente da venda (`PrecoAcimaDoLimite`).

No serviço `alterar_preco()`, `memento = venda.salvar_preco()` é chamado antes da troca, mas
`historico.guardar(memento)` só é executado **depois** que `venda.alterar_preco(novo_preco)` passa
sem exceção — garantindo que tentativas inválidas (como preço acima do teto ou venda encerrada) não
sujem a pilha de mementos.

### Diagrama de classes (Mermaid)

```mermaid
classDiagram
    class Venda {
        +str id
        +str ticket_id
        +str vendedor_id
        +Decimal preco
        +Decimal valor_original
        +StatusVenda status
        +PoliticaTetoPercentual politica_preco
        +alterar_preco(novo_preco: Decimal) None
        +salvar_preco() MementoPrecoVenda
        +restaurar_preco(memento: MementoPrecoVenda) None
        -_validar_preco(preco: Decimal) None
        -_exigir_ativa(acao: str) None
    }

    class MementoPrecoVenda {
        -str _venda_id
        -Decimal _preco
        +venda_id() str
    }

    class AbstractHistoricoDePrecos {
        <<abstract>>
        +guardar(memento: MementoPrecoVenda)* None
        +desempilhar(venda_id: str)* MementoPrecoVenda | None
    }

    class SqlAlchemyHistoricoDePrecos {
        +Session session
        +guardar(memento: MementoPrecoVenda) None
        +desempilhar(venda_id: str) MementoPrecoVenda | None
    }

    class FakeHistoricoDePrecos {
        -dict~str, list~MementoPrecoVenda~~ _pilhas
        +guardar(memento: MementoPrecoVenda) None
        +desempilhar(venda_id: str) MementoPrecoVenda | None
    }

    class ServicesPreco {
        <<service_layer>>
        +alterar_preco(venda_id: str, novo_preco: Decimal, vendas, historico, session) Venda
        +desfazer_alteracao_de_preco(venda_id: str, vendas, historico, session) Venda
    }

    Venda ..> MementoPrecoVenda : cria e lê _preco (interface larga)
    AbstractHistoricoDePrecos o-- MementoPrecoVenda : guarda por venda_id (interface estreita)
    AbstractHistoricoDePrecos <|-- SqlAlchemyHistoricoDePrecos
    AbstractHistoricoDePrecos <|-- FakeHistoricoDePrecos
    ServicesPreco ..> Venda : salvar_preco() / restaurar_preco()
    ServicesPreco ..> AbstractHistoricoDePrecos : guardar() / desempilhar()
```

### Teste

Os testes novos estão divididos nas três camadas da suíte:

| Testes | O que conferem |
| :--- | :--- |
| `tests/unit/test_venda_memento.py` (16 testes) | **Originator e Memento (9 testes):** `salvar_preco()` e `restaurar_preco()` devolvem o preço anterior; múltiplos mementos restauram em ordem LIFO; `MementoPrecoVenda` expõe apenas `venda_id` (interface estreita: sem atributo público `preco` e sem vazar o valor no `repr`); `salvar_preco()` não é afetado por mudanças posteriores na `Venda`; `restaurar_preco()` recusa venda `CANCELADA` e `CONCLUIDA` (`VendaEncerrada`), recusa memento de outra venda (`MementoDeOutraVenda`) e revalida a `PoliticaTetoPercentual` vigente (`PrecoAcimaDoLimite`). **Serviços com fakes (7 testes):** `alterar_preco` atualiza o preço e empilha o memento; `desfazer_alteracao_de_preco` restaura o preço anterior e suporta múltiplos níveis LIFO; desfazer sem histórico lança `SemAlteracaoDePreco`; venda inexistente lança `VendaNaoEncontrada`; falha em `alterar_preco` (acima do teto) não empilha memento; falha em `desfazer_alteracao_de_preco` (venda encerrada) não faz commit. |
| `tests/integration/test_historico_precos.py` (5 testes) | `SqlAlchemyHistoricoDePrecos` persiste na tabela `historico_precos` e desempilha o último preço salvo; múltiplos mementos da mesma venda saem em ordem LIFO (`ORDER BY id DESC`) e são removidos da tabela ao desempilhar; venda sem histórico retorna `None`; pilhas de vendas distintas não interferem entre si; fluxo completo de `services.alterar_preco` e `services.desfazer_alteracao_de_preco` contra sessão SQLite real. |
| `tests/e2e/test_preco_api.py` (6 testes) | Rotas HTTP `PUT /anuncios/<venda_id>/preco` e `POST /anuncios/<venda_id>/preco/desfazimento`: alteração e desfazimento em múltiplos passos retornam `200`; desfazer sem histórico retorna `409` (`SemAlteracaoDePreco`); preço acima do teto de 110% retorna `400` e preserva o preço atual; anúncio inexistente retorna `404` nas duas rotas; anúncio já cancelado recusa desfazimento com `400` (`VendaEncerrada`). |

Na suíte completa, os 256 testes que existiam antes do commit `7435b36` continuaram passando sem
nenhuma linha de teste existente modificada, somados aos 27 testes novos:

```text
$ git show 7435b36 --stat
 src/rocketicket/adapters/orm.py            |  29 ++++-
 src/rocketicket/adapters/repository.py     |  45 +++++++
 src/rocketicket/domain/model.py            |  34 ++++++
 src/rocketicket/entrypoints/flask_app.py   |  24 ++++
 src/rocketicket/service_layer/services.py  |  54 ++++++++-
 tests/conftest.py                          |  24 ++++
 tests/e2e/test_preco_api.py                |  54 +++++++++
 tests/integration/test_historico_precos.py |  74 ++++++++++++
 tests/unit/test_venda_memento.py           | 186 +++++++++++++++++++++++++++++
 9 files changed, 520 insertions(+), 2 deletions(-)

$ pytest tests          # em 7435b36^ (a4f0292): 256 passed
$ pytest tests          # em 7435b36:            283 passed
```

### Custo

- **Volume e novas estruturas:** a mudança somou `+520` e `-2` linhas em 9 arquivos, introduzindo
  uma classe de domínio (`MementoPrecoVenda`), duas exceções (`MementoDeOutraVenda` e
  `SemAlteracaoDePreco`), uma porta e dois adaptadores de histórico (`AbstractHistoricoDePrecos`,
  `SqlAlchemyHistoricoDePrecos`, `FakeHistoricoDePrecos`), uma tabela relacional
  (`historico_precos`), dois casos de uso e duas rotas HTTP.
- **Ausência de `friend` em Python:** como a linguagem não impõe visibilidade por classe amiga, a
  separação entre interface estreita e interface larga depende da convenção `_preco` e exige
  propriedades explícitas (`_id`, `_venda_id`, `_preco`) no mapeamento imperativo do SQLAlchemy em
  `_mapear_historico_precos()`.
- **Custos de armazenamento do Caretaker (Consequência 5 do GoF):** cada chamada bem-sucedida a
  `alterar_preco()` insere uma linha em `historico_precos`. Como o *Caretaker* não conhece o
  conteúdo nem o ciclo de vida interno da `Venda`, mementos empilhados de um anúncio que depois é
  concluído ou cancelado permanecem na tabela sem poderem mais ser restaurados (já que
  `restaurar_preco()` recusa vendas encerradas). Em produção, isso exigiria limpeza ao encerrar a
  venda ou um limite de profundidade na pilha por anúncio.

**Por que compensa.** A `Venda` continua coesa — preocupada apenas com o estado do anúncio e com a
`PoliticaTetoPercentual` — sem carregar listas de histórico nem conhecer a tabela
`historico_precos`. Ao mesmo tempo, o desfazimento nunca fura o domínio: toda restauração passa
obrigatoriamente por `Venda.restaurar_preco()`, que garante que venda encerrada não muda de preço e
que nenhuma regra anti-cambismo é contornada. Trocar a estratégia de retenção do histórico (por
exemplo, limitar a pilha aos últimos 5 preços ou limpar ao concluir a venda) mexe apenas no
*Caretaker* (`SqlAlchemyHistoricoDePrecos`), sem tocar na entidade `Venda`.

## Miguel — Observer

### Nome e categoria

<!--
Responsável: Miguel
O enunciado exige: o nome do padrão e a sua categoria no GoF.
-->

### Contexto e problema

<!--
Responsável: Miguel
O enunciado exige: o contexto e o problema real do domínio que o padrão resolve.
-->

### Alternativa considerada

<!--
Responsável: Miguel
O enunciado exige: a alternativa considerada.
-->

### Participantes (classes reais)

<!--
Responsável: Miguel
O enunciado exige: os participantes do padrão, mapeados para as classes reais do código.
-->

### Diagrama de classes (Mermaid)

<!--
Responsável: Miguel
O enunciado exige: o diagrama de classes em Mermaid, com a fonte em texto neste arquivo.
-->

### Teste

<!--
Responsável: Miguel
O enunciado exige: o teste que cobre o padrão.
-->

### Custo

<!--
Responsável: Miguel
O enunciado exige: o custo de introduzir o padrão.
-->

## Guilherme — Adapter

### Nome e categoria

<!--
Responsável: Guilherme
O enunciado exige: o nome do padrão e a sua categoria no GoF.
-->

**Adapter**, padrão **estrutural** do GoF, na variante de objeto (por composição). Ele
converte a interface de uma classe em outra que o cliente espera, permitindo que classes
com interfaces incompatíveis trabalhem juntas.

### Contexto e problema

<!--
Responsável: Guilherme
O enunciado exige: o contexto e o problema real do domínio que o padrão resolve.
-->

Um pedido só pode ser confirmado com o pagamento aprovado (ADR 0005). Até a entrega da
Fase 1, ninguém cobrava de fato: a rota `POST /pedidos/<id>/confirmacao` recebia
`pagamento_aprovado: true/false` no JSON, e o `confirmar_pedido` aprovava ou recusava o
pagamento conforme esse booleano. Na prática, era o próprio comprador que dizia se tinha
pago.

O passo natural é cobrar o pedido em um gateway de pagamento externo. Nesta entrega, esse
gateway é simulado por `ClienteGatewayExterno` (`adapters/gateway_simulado.py`), que faz o
papel do SDK de um fornecedor: código de terceiros que o RocketTicket não pode alterar. A
interface dele não combina com a do domínio:

| O que o domínio tem | O que o gateway externo espera ou devolve |
| :--- | :--- |
| `valor: Decimal` em reais (`105.00`) | `"amount_cents": int` em centavos (`10500`) |
| `pedido_id`, `token_pagamento` | dicionário com `"order_ref"`, `"card_token"` e `"currency": "BRL"` |
| pagamento aprovado ou recusado | `{"status": "approved" \| "declined" \| "error", "reason": ...}` |
| falha é exceção | falha volta como `"status": "error"`, sem exceção |

Sem um adaptador, essas conversões entrariam no `confirmar_pedido`: o service passaria a
conhecer centavos, chaves em inglês e os textos de status do fornecedor. Trocar de
fornecedor, ou usar um gateway falso nos testes, exigiria editar o caso de uso.

### Alternativa considerada

<!--
Responsável: Guilherme
O enunciado exige: a alternativa considerada.
-->

1. **Chamar o `ClienteGatewayExterno` direto no `confirmar_pedido`.** É menos código, mas
   amarra o caso de uso ao formato de um fornecedor. A conversão de `Decimal` para
   centavos e o mapeamento de `"approved"`/`"declined"`/`"error"` ficariam misturados à
   regra do pedido, e os testes unitários do service precisariam montar respostas no
   formato do fornecedor. Rejeitada.
2. **Adapter de classe (herdar de `GatewayDePagamento` e de `ClienteGatewayExterno` ao
   mesmo tempo).** Python permite herança múltipla, mas o adaptador passaria a expor
   `create_charge()` ao service e ficaria preso a uma única classe de cliente. A versão
   de objeto recebe o cliente no construtor, o que deixa trocar o cliente (inclusive por
   um espião, nos testes) sem criar subclasses. Rejeitada em favor do adapter de objeto.
3. **Manter o booleano `pagamento_aprovado` vindo do JSON.** Não resolve o problema: o
   cliente HTTP continuaria decidindo se o pagamento foi aprovado.

### Participantes (classes reais)

<!--
Responsável: Guilherme
O enunciado exige: os participantes do padrão, mapeados para as classes reais do código.
-->

| Papel no GoF | Classe real | Arquivo |
| :--- | :--- | :--- |
| **Target** | `GatewayDePagamento` (`cobrar(pedido_id, valor, token_pagamento) -> bool`) | `src/rocketicket/adapters/pagamento.py` |
| **Adapter** | `AdaptadorGatewayExterno` | `src/rocketicket/adapters/pagamento.py` |
| **Adaptee** | `ClienteGatewayExterno` (`create_charge(payload: dict) -> dict`) | `src/rocketicket/adapters/gateway_simulado.py` |
| **Client** | `services.confirmar_pedido` | `src/rocketicket/service_layer/services.py` |

O `AdaptadorGatewayExterno` traduz nos dois sentidos:

- **Na ida:** converte `Decimal` em centavos inteiros sem arredondar (fração de centavo
  lança `ValueError` antes de chamar o fornecedor) e monta o payload com `amount_cents`,
  `currency`, `order_ref` e `card_token`.
- **Na volta:** `"approved"` vira `True` e `"declined"` vira `False`. `"error"`, ou
  qualquer resposta fora do contrato, vira a exceção `GatewayIndisponivel`, que a API
  devolve como `502`.

A composição fica no `create_app()`, que por padrão monta
`AdaptadorGatewayExterno(ClienteGatewayExterno())` e aceita outro `GatewayDePagamento` pelo
parâmetro `gateway_de_pagamento`. Nos testes, o `FakeGatewayDePagamento` (`tests/conftest.py`)
implementa o mesmo Target sem passar pelo Adaptee.

Para a simulação, o `ClienteGatewayExterno` decide pelo token, como os ambientes de teste
dos gateways reais: `tok_aprovado` aprova, `tok_recusado` recusa, `tok_falha` devolve
erro e qualquer outro token é recusado.

### Diagrama de classes (Mermaid)

<!--
Responsável: Guilherme
O enunciado exige: o diagrama de classes em Mermaid, com a fonte em texto neste arquivo.
-->

```mermaid
classDiagram
    direction LR

    class confirmar_pedido {
        <<service>>
        +confirmar_pedido(pedido_id, token_pagamento, repo_pedidos, repo_tickets, gateway, session) bool
    }

    class GatewayDePagamento {
        <<abstract>>
        +cobrar(pedido_id: str, valor: Decimal, token_pagamento: str) bool
    }

    class AdaptadorGatewayExterno {
        +MOEDA = "BRL"
        -cliente: ClienteGatewayExterno
        +cobrar(pedido_id: str, valor: Decimal, token_pagamento: str) bool
        -_em_centavos(valor: Decimal) int
    }

    class ClienteGatewayExterno {
        +create_charge(payload: dict) dict
    }

    class FakeGatewayDePagamento {
        +cobrancas: list
        +cobrar(pedido_id, valor, token_pagamento) bool
    }

    class GatewayIndisponivel {
        <<exception>>
    }

    class Pedido {
        +exigir_cobranca_pendente()
        +aprovar_pagamento()
        +recusar_pagamento()
        +confirmar(status_ticket)
    }

    confirmar_pedido ..> GatewayDePagamento : cobra
    confirmar_pedido ..> Pedido : aprova ou recusa
    GatewayDePagamento <|-- AdaptadorGatewayExterno : Adapter
    GatewayDePagamento <|-- FakeGatewayDePagamento : testes
    AdaptadorGatewayExterno o--> ClienteGatewayExterno : delega (Adaptee)
    AdaptadorGatewayExterno ..> GatewayIndisponivel : lança
```

### Teste

<!--
Responsável: Guilherme
O enunciado exige: o teste que cobre o padrão.
-->

- **`tests/unit/test_gateway_pagamento.py`** cobre o Adapter isolado. Com um
  `ClienteEspiao` no lugar do Adaptee, verifica o payload montado, a conversão para
  centavos (`0.01 -> 1`, `110.5 -> 11050`, `1000 -> 100000`), a recusa de fração de
  centavo sem chamar o fornecedor e a tradução de `approved`, `declined`, `error` e de
  respostas fora do contrato. Com o `ClienteGatewayExterno` de verdade, cobre os quatro
  tipos de token e o valor zero.
- **`tests/unit/test_services_pedido.py::TestConfirmarPedido`** usa o
  `FakeGatewayDePagamento` e verifica que o service cobra o valor do pedido com o token
  recebido. Verifica também que **não** cobra quando o pedido não existe, o ticket não
  existe, o pedido já foi confirmado ou cancelado, ou o pagamento já foi recusado. Se o
  gateway falhar, nada é salvo e o pagamento continua `PENDENTE`.
- **`tests/unit/test_pedido.py::TestExigirCobrancaPendente`** cobre a nova checagem do
  agregado.
- **`tests/e2e/test_pedido_api.py`** passa pela API com o adaptador e o gateway simulado
  reais. Aprovação, recusa e token desconhecido devolvem `200`. Falha do gateway devolve
  `502` e deixa tentar de novo. Token ausente ou inválido devolve `400`. Há também um teste
  que injeta um gateway pelo `create_app()`.

A suíte foi de 296 para 326 testes, todos passando com `python -m pytest tests`.

### Custo

<!--
Responsável: Guilherme
O enunciado exige: o custo de introduzir o padrão.
-->

- **Código novo:** dois módulos (`pagamento.py`, 68 linhas, e `gateway_simulado.py`, 49
  linhas) e uma exceção a mais (`GatewayIndisponivel`), tratada em `erros.py`. Para uma
  única chamada ao fornecedor, é uma camada a mais para ler.
- **Mudança de contrato da API:** a confirmação passou de `{"pagamento_aprovado": bool}`
  para `{"token_pagamento": "..."}`. Quem chamava a rota antiga precisa mudar. Na suíte, isso
  alterou os testes e2e do Pedido e uma linha do teste de injeção do Caio
  (`tests/integration/test_ticket_repository_injection.py`), que passa pela confirmação.
- **Checagem nova no domínio:** como a cobrança acontece fora do sistema, antes de
  `aprovar_pagamento()`, o Pedido ganhou `exigir_cobranca_pendente()`. Sem ela, um pedido
  já confirmado seria cobrado de novo antes de o domínio recusar a operação.
- **Limitação conhecida:** a disponibilidade do ticket só é checada pelas regras de
  confirmação, depois da cobrança. Se o ticket deixar de estar `ANUNCIADO`, o gateway
  aprova, o Pedido lança `TicketIndisponivel` e nada é salvo, mas o comprador foi cobrado.
  Com um fornecedor real, isso exigiria pré-autorização e captura, ou estorno. O id da
  cobrança (`charge_id`) também não é persistido, porque o Pagamento ainda não tem esse
  campo (ADR 0005).

Compensa porque o caso de uso fala só a língua do domínio (`cobrar(...) -> bool`). Trocar
de fornecedor é escrever outro adaptador e passá-lo ao `create_app()`, sem tocar no
`confirmar_pedido`. Os testes do service também não dependem do formato de nenhum gateway.
