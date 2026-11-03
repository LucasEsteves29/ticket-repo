# SOLID no RocketTicket

Documento do checkpoint 2 da Fase 2 (tag `fase2-checkpoint-2`, prazo 03/11/2026 às 23h59 BRT).

Cada integrante corrige uma violação de um princípio SOLID no próprio agregado ou módulo,
e o grupo cobre pelo menos 3 princípios diferentes. O código "antes" de cada seção vem de um
commit anterior a 06/10/2026: nenhuma violação foi criada para ser corrigida. Cada seção tem
duas partes. Em "Antes" fica a violação, e em "Depois", a refatoração feita em commit do
próprio autor.

## Lucas — SRP (`entrypoints/flask_app.py`)

### Antes

<!--
Responsável: Lucas
O enunciado exige:
- o princípio violado;
- o trecho do código;
- o hash do commit anterior a 06/10;
- o problema concreto que a violação causa.
-->

**Princípio violado:** SRP, o Princípio da Responsabilidade Única. Um módulo deve ter um
único motivo para mudar.

**Commit "antes":** `f85f2d4` (Lucas Esteves, 29/09/2026), `FEAT: adiciona base do app Flask
e endpoint POST /tickets com testes e2e`. O código abaixo é o do arquivo nesse commit
(`git show f85f2d4:src/rocketicket/entrypoints/flask_app.py`).

**A violação.** O `flask_app.py` nasceu com 86 linhas, das quais a `create_app()` ocupa as
linhas 13 a 60. A função e o módulo acumulam quatro responsabilidades, cada uma com um
motivo de mudança diferente:

| Responsabilidade | Onde fica em `f85f2d4` | Muda quando |
|---|---|---|
| Montar o app e a sessão por requisição | `create_app()`: `orm.start_mappers()`, `Flask(__name__)`, `abrir_sessao()` e `fechar_sessao()` (linhas 13 a 25) | muda a infraestrutura: banco, ciclo de vida da sessão |
| Traduzir exceções em códigos HTTP | quatro `@app.errorhandler` dentro de `create_app()` (linhas 27 a 41) | muda o contrato de erro da API: formato do corpo, código de cada erro |
| Validar e converter a entrada JSON | `_ler_json`, `_ler_texto` e `_ler_decimal`, no nível do módulo (linhas 63 a 86) | muda a regra de entrada, como o formato aceito para dinheiro |
| Declarar as rotas de todos os agregados | `POST /tickets` dentro de `create_app()` (linhas 43 a 54) e os marcadores `# endpoints de Venda: Igor` e `# endpoints de Pedido: Guilherme` (linhas 56 e 58) | muda qualquer caso de uso de qualquer agregado |

Os dois marcadores mostram que a violação já estava no desenho: o arquivo reservava, dentro
da mesma função, o lugar onde outros dois integrantes iam escrever as rotas dos seus agregados.

Trecho de `f85f2d4` (as partes omitidas estão marcadas com `# (...)`):

```python
def create_app(session_factory):
    orm.start_mappers()
    app = Flask(__name__)

    @app.before_request
    def abrir_sessao():
        g.session = session_factory()

    # (...) fechar_sessao()

    @app.errorhandler(model.ErroDeDominio)
    def erro_de_dominio(e):
        return {"erro": str(e)}, 400

    # (...) mais três errorhandlers: ErroDeServico, RecursoNaoEncontrado e HTTPException

    @app.post("/tickets")
    def emitir_ticket():
        dados = _ler_json(CAMPOS_TICKET)
        # (...) chama services.emitir_ticket e devolve 201

    # endpoints de Venda: Igor

    # endpoints de Pedido: Guilherme

    return app


def _ler_decimal(dados, campo):
    try:
        valor = Decimal(dados[campo]) if isinstance(dados[campo], str) else None
    except InvalidOperation:
        valor = None
    if valor is None or not valor.is_finite() or valor.as_tuple().exponent < -2:
        abort(400, f"{campo} inválido")
    return valor
```

**Problema concreto.** O histórico do arquivo mostra três integrantes editando o mesmo arquivo
por motivos diferentes, todos no mesmo dia:

```text
$ git log --format='%h %an %ad %s' --date=short -- src/rocketicket/entrypoints/flask_app.py
835565f guilhermeboechat 2026-09-29 feat(pedido): add endpoints e testes e2e
19cc75c igorbleal 2026-09-29 fix(api): adicionando passagem do repositorio de tickets na rota de criar anuncio
e17c50a igorbleal 2026-09-29 feat(entrypoints): adiciona endpoint POST /anuncios e testes e2e
f85f2d4 Lucas Esteves 2026-09-29 FEAT: adiciona base do app Flask e endpoint POST /tickets com testes e2e
```

O que cada commit mudou no arquivo (`git show --numstat` e o diff de cada um):

| Commit | Autor | Linhas (+/−) | O que mudou | Responsabilidade tocada |
|---|---|---|---|---|
| `f85f2d4` | Lucas | +86 / −0 | cria o app, a sessão, os tratadores de erro, os helpers de leitura e `POST /tickets` | as quatro |
| `e17c50a` | Igor | +13 / −1 | `CAMPOS_ANUNCIO` e `POST /anuncios` | rotas (Venda) |
| `19cc75c` | Igor | +1 / −0 | passa `SqlAlchemyTicketRepository` para o `criar_anuncio` na rota | rotas (Venda) |
| `835565f` | Guilherme | +42 / −0 | `CAMPOS_PEDIDO`, `CAMPOS_CONFIRMACAO`, as rotas `POST /pedidos`, `/pedidos/<id>/confirmacao` e `/pedidos/<id>/cancelamento`, e o helper `_ler_booleano` | rotas (Pedido) e validação da entrada |

O commit `835565f` mostra o problema num commit só: para criar as rotas do Pedido, o Guilherme
também precisou de uma regra de entrada nova (`_ler_booleano`) e a colocou entre os helpers
`_ler_texto` e `_ler_decimal`. Hoje (`HEAD` = `fbf6358`) o arquivo tem 141 linhas, e o
`git blame` divide a autoria entre três pessoas:

```text
$ git blame --line-porcelain HEAD -- src/rocketicket/entrypoints/flask_app.py | grep '^author ' | sort | uniq -c
     85 author Lucas Esteves
     42 author guilhermeboechat
     14 author igorbleal
```

Os efeitos:

- **Mudar a validação de dinheiro mexe nas rotas de dois agregados.** O `_ler_decimal` é usado
  pelo `POST /tickets` (`valor_original`, linha 51 no `HEAD`) e pelo `POST /anuncios`
  (`preco`, linha 66). Uma mudança pensada para um agregado, como aceitar outro formato de
  preço, muda o outro endpoint junto, e a edição acontece no arquivo onde estão as rotas dos
  três agregados.
- **Mudar o formato de erro mexe na função que declara todas as rotas.** Os quatro tratadores
  de erro estão dentro de `create_app()`, ao lado das rotas de Ticket, Venda e Pedido, e
  definem o corpo `{"erro": ...}` de todas as respostas de erro. Nos testes e2e, 25 linhas de
  asserção dependem dessa chave: 23 `assert "erro" in resposta.get_json()` e 2 comparações
  com `{"erro": "ticket t9 não existe"}`, espalhadas por `test_erros_api.py`,
  `test_pedido_api.py`, `test_ticket_api.py` e `test_venda_api.py`
  (`git grep -h '"erro"' HEAD -- tests/e2e`). Uma mudança no formato quebra endpoints e testes
  dos três agregados, e quem a faz precisa editar o código dos outros.
- **Risco de conflito.** As rotas de Venda e de Pedido foram escritas no mesmo dia, dentro da
  mesma função e no mesmo arquivo que concentra a infraestrutura e as regras de entrada.
  Qualquer mudança numa dessas responsabilidades gera um diff no arquivo em que os outros
  integrantes estão trabalhando nas suas rotas. Isso aumenta a chance de conflito no merge e
  de quebrar sem querer o endpoint de outro agregado.

### Depois

<!--
Responsável: Lucas
O enunciado exige:
- o hash do commit da refatoração (do próprio autor);
- o que mudou;
- como os testes garantiram que o comportamento não mudou;
- o custo da mudança e por que compensa.
-->

## Caio — DIP

### Antes

<!--
Responsável: Caio
O enunciado exige:
- o princípio violado;
- o trecho do código;
- o hash do commit anterior a 06/10;
- o problema concreto que a violação causa.
-->

**Princípio violado:** DIP, o Princípio da Inversão de Dependência. O código de alto nível
(a rota HTTP, que coordena a emissão do ticket) não deve depender diretamente do detalhe
de persistência SQLAlchemy; ambos devem depender de uma abstração.

**Commit "antes":** `f85f2d4` (Lucas Esteves, 29/09/2026), `FEAT: adiciona base do app Flask
e endpoint POST /tickets com testes e2e`. Esse commit é anterior a 06/10/2026. O service
`emitir_ticket` já recebe um `AbstractRepository[Ticket]`, mas a rota instancia o adaptador
concreto no próprio endpoint:

```python
# src/rocketicket/entrypoints/flask_app.py (f85f2d4)
from rocketicket.adapters import orm, repository

@app.post("/tickets")
def emitir_ticket():
    dados = _ler_json(CAMPOS_TICKET)
    ticket_id = services.emitir_ticket(
        _ler_texto(dados, "id"),
        _ler_texto(dados, "evento_id"),
        _ler_decimal(dados, "valor_original"),
        _ler_texto(dados, "dono_id"),
        repository.SqlAlchemyTicketRepository(g.session),  # detalhe concreto na rota
        g.session,
    )
    return {"id": ticket_id}, 201
```

O ponto de acoplamento é a construção de `SqlAlchemyTicketRepository(g.session)` na rota.
Embora `services.emitir_ticket` trabalhe com a abstração `AbstractRepository[Ticket]`, a
camada HTTP importa o módulo de adapters e escolhe diretamente SQLAlchemy. Assim, trocar a
persistência ou testar a rota com um repositório fake exige alterar ou contornar o código da
rota; a dependência concreta também impede configurar essa escolha na composição da aplicação.

**Problema concreto.** Em `f85f2d4`, a fábrica da aplicação recebe apenas
`create_app(session_factory)`. Mesmo passando uma sessão falsa, cada requisição a
`POST /tickets` continua construindo `SqlAlchemyTicketRepository` dentro do endpoint.
Esse adaptador chama `session.get(model.Ticket, id)` e `session.add(ticket)`, portanto
o teste da rota fica vinculado à interface da sessão SQLAlchemy. Para usar um
`FakeTicketRepository` que implemente apenas o contrato `add()`/`get()`, seria preciso
alterar a rota ou substituir a classe importada com um patch no teste. A abstração já
aceita pelo service não pode ser escolhida por quem monta a aplicação.

Essa evidência pode ser conferida sem depender da versão atual da branch:

```sh
git show f85f2d4:src/rocketicket/entrypoints/flask_app.py
git show f85f2d4:src/rocketicket/service_layer/services.py
git show c13cc33:src/rocketicket/adapters/repository.py
```

A instanciação concreta deve ficar na composição da aplicação; o ponto identificado
para o C2 é permitir que a rota receba o repositório por injeção de dependência.

O histórico confirma que a implementação concreta foi introduzida antes da rota: `c13cc33`
(Caio, 28/09/2026) adicionou `SqlAlchemyTicketRepository`, e `f85f2d4` o instanciou dentro
do endpoint `POST /tickets` no dia seguinte. A abstração usada pelo service está em
`60679da` (`AbstractRepository`), também anterior a 06/10/2026.

### Depois

<!--
Responsável: Caio
O enunciado exige:
- o hash do commit da refatoração (do próprio autor);
- o que mudou;
- como os testes garantiram que o comportamento não mudou;
- o custo da mudança e por que compensa.
-->

## Igor — SRP (domain/model.py e service_layer/services.py)

### Antes

**Princípio violado:** SRP, o Princípio da Responsabilidade Única. Uma classe deve ter um único motivo para mudar.

**Commit "antes":** `331685a` (Igor Leal, 24/09/2026), `fix(venda): arredonda teto de 110% para baixo com quantize na criacao`. O código abaixo é o do bloco da `Venda` nesse commit (`git show 331685a:src/rocketicket/domain/model.py`, linhas 170 a 224).

### A violação

No commit `331685a`, a classe `Venda` ocupa as linhas 170 a 234 de `model.py`. Ela acumula duas responsabilidades, cada uma com um motivo de mudança diferente:

| Responsabilidade | Onde fica em `331685a` | Muda quando |
|---|---|---|
| Controlar o ciclo de vida e a identidade do anúncio | `__init__()` (atributos e status inicial `StatusVenda.ATIVA`), `alterar_preco()`, `cancelar()`, `concluir()` e `_exigir_ativa()` (linhas 173 a 187 e 198 a 224) | Muda o ciclo de vida do anúncio: estados possíveis, regras de cancelamento ou conclusão |
| Calcular e validar a política financeira do teto de revenda | `_validar_preco()` com o fator fixo `Decimal("1.10")` e o truncamento `quantize(Decimal("0.01"), rounding=ROUND_DOWN)` (linhas 189 a 196), além do cálculo repetido em `alterar_preco()` (linhas 201 a 205) | Muda a regra anti-cambismo: percentual máximo permitido, critério de arredondamento em centavos ou limite por tipo de ingresso |

Trecho de `331685a` (as partes omitidas estão marcadas com `# (...)`):

```python
class Venda:
    """Raiz do agregado Venda."""

    def __init__(
        self,
        id: str,
        ticket_id: str,
        vendedor_id: str,
        preco: Decimal,
        valor_original: Decimal,
    ):
        self.id = id
        self.ticket_id = ticket_id
        self.vendedor_id = vendedor_id
        self.valor_original = valor_original
        self._validar_preco(preco)
        self.preco = preco
        self.status = StatusVenda.ATIVA

    def _validar_preco(self, preco: Decimal) -> None:
        limite_maximo = (self.valor_original * Decimal("1.10")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        if preco > limite_maximo:
            raise PrecoAcimaDoLimite(
                f"Preço {preco} excede o limite máximo permitido de 110% ({limite_maximo})"
            )

    def alterar_preco(self, novo_preco: Decimal) -> None:
        """Troca o preço do anúncio, respeitando o mesmo limite de 110% da criação."""
        self._exigir_ativa("ter o preço alterado")
        limite_maximo = self.valor_original * Decimal("1.10")
        if novo_preco > limite_maximo:
            raise PrecoAcimaDoLimite(
                f"Preço {novo_preco} excede o limite máximo permitido de 110% ({limite_maximo})"
            )
        self.preco = novo_preco

    # (...) cancelar(), concluir() e _exigir_ativa()
```

### Problema concreto

O histórico de `model.py` mostra três integrantes editando a classe `Venda` porque o ciclo de vida do anúncio e a fórmula financeira do teto de 110% moram na mesma classe:

```text
$ git log --format='%h %an %ad %s' --date=short -- src/rocketicket/domain/model.py
be76d28 Miguel Bocanera 2026-09-29 fix(repository): correct typos in Venda repository and model documentation
186b52c Lucas Esteves 2026-09-26 FIX: alterar_preco usa o mesmo teto de 110% do __init__
331685a igorbleal 2026-09-24 fix(venda): arredonda teto de 110% para baixo com quantize na criacao
0a468e7 Miguel Bocanera 2026-09-22 feat(venda): alterar_preco(), cancelar() e concluir() bloqueando venda encerrada
cdd0311 igorbleal 2026-09-21 Feat: Criando entidade Venda
```

O que cada commit mudou na classe `Venda` (`git show --numstat` e o diff de cada um):

| Commit | Autor | Linhas (+/−) | O que mudou | Responsabilidade tocada |
|---|---|---|---|---|
| `cdd0311` | Igor | +36 / −1 | cria `StatusVenda`, `PrecoAcimaDoLimite` e `Venda.__init__` com `valor_original * Decimal("1.10")` | ciclo de vida e política de teto |
| `0a468e7` | Miguel | +31 / −0 | cria `VendaEncerrada`, `alterar_preco()`, `cancelar()`, `concluir()` e `_exigir_ativa()`, repetindo o cálculo de 1.10 em `alterar_preco()` | ciclo de vida e política de teto |
| `331685a` | Igor | +12 / −9 | extrai `_validar_preco()` com `quantize(..., rounding=ROUND_DOWN)` chamado no `__init__`, mas `alterar_preco()` continua com o cálculo antigo | política de teto |
| `186b52c` | Lucas | +1 / −5 | substitui o cálculo em `alterar_preco()` por `self._validar_preco(novo_preco)` | ciclo de vida e política de teto |

Os commits `331685a` e `186b52c` mostram o problema na prática: quando a regra financeira do teto mudou para truncar centavos com `ROUND_DOWN` (`331685a`), a edição aconteceu dentro de `Venda`, e `alterar_preco()` continuou aplicando `self.valor_original * Decimal("1.10")` sem `quantize` até o commit `186b52c` corrigir a divergência dois dias depois.

No HEAD, o bloco da `Venda` (linhas 156 a 241) divide a autoria entre três pessoas no `git blame`:

```text
$ git blame -L 156,241 --line-porcelain fbf6358 -- src/rocketicket/domain/model.py | grep '^author ' | sort | uniq -c
    47 author igorbleal
    38 author Miguel Bocanera
    1 author Lucas Esteves
```

### Os efeitos

- **Mudar a regra financeira do teto obriga a editar a entidade `Venda`.** O fator `Decimal("1.10")` e a chamada a `quantize(Decimal("0.01"), rounding=ROUND_DOWN)` estão embutidos dentro de `Venda._validar_preco()` (linhas 201 a 203 no HEAD). Qualquer ajuste na política de preço — como alterar o percentual permitido, mudar a regra de arredondamento ou exigir revenda pelo preço de face (100%, sem ágio) em lotes promocionais — exige modificar a classe que controla o ciclo de vida do anúncio.
- **Não é possível consultar nem testar o cálculo do teto sem instanciar uma `Venda`.** A fórmula que calcula o preço máximo permitido para um `valor_original` não devolve o valor calculado: ela só existe dentro de `_validar_preco()`, acoplada ao lançamento de `PrecoAcimaDoLimite`. Nos testes (`git grep -h 'PrecoAcimaDoLimite' fbf6358 -- tests/`), as 11 ocorrências precisam criar uma instância inteira de `Venda` (ou chamar `criar_anuncio`) apenas para exercitar a aritmética do limite de 110%.
- **Acoplamento no caso de uso `criar_anuncio`.** Em `service_layer/services.py` (commit `38e541d`, linhas 48 a 72 no HEAD), `criar_anuncio` instancia `model.Venda(...)` sem poder parametrizar a política de preço, prendendo o serviço a uma única regra fixa de 110%.

### Depois

<!--
Responsável: Igor
O enunciado exige:
- o hash do commit da refatoração (do próprio autor);
- o que mudou;
- como os testes garantiram que o comportamento não mudou;
- o custo da mudança e por que compensa.
-->

## Miguel — ISP (`adapters/repository.py`)

### Antes

<!--
Responsável: Miguel
O enunciado exige:
- o princípio violado;
- o trecho do código;
- o hash do commit anterior a 06/10;
- o problema concreto que a violação causa.
-->

**Princípio violado:** ISP, o Princípio da Segregação de Interfaces. Um cliente não deve
ser obrigado a depender de métodos que não usa.

**Commits "antes":** `73b9847` (Miguel, 28/09/2026), que cria a `AbstractVendaRepository`,
e `54e16d6` (Miguel, 28/09/2026), que cria o `SqlAlchemyVendaRepository`. O único cliente
da consulta é o `criar_pedido`, do Guilherme, em `ec01929` (29/09/2026).

**A violação.** A consulta `get_ativa_por_ticket()` foi criada para atender o Pedido, mas
ficou presa dentro do repositório completo da Venda. Para usar só ela, o `criar_pedido`
recebe uma interface que também sabe gravar e buscar vendas:

```python
# adapters/repository.py (73b9847 e 54e16d6)
class AbstractVendaRepository(AbstractRepository[model.Venda]):
    # herda add(venda) e get(id) da AbstractRepository

    @abc.abstractmethod
    def get_ativa_por_ticket(self, ticket_id: str) -> model.Venda | None:
        raise NotImplementedError


# service_layer/services.py (ec01929)
def criar_pedido(
    id, ticket_id, comprador_id,
    repo_pedidos: AbstractRepository[model.Pedido],
    repo_vendas: AbstractVendaRepository,      # depende de add, get e get_ativa_por_ticket
    session,
) -> str:
    venda = repo_vendas.get_ativa_por_ticket(ticket_id)   # o único método usado
    # (...) cria o Pedido com venda.preco e grava em repo_pedidos
```

| Método da `AbstractVendaRepository` | Usado pelo `criar_pedido`? |
|---|---|
| `add(venda)` | não |
| `get(id)` | não |
| `get_ativa_por_ticket(ticket_id)` | sim |

A interface foi pensada para o agregado, e não para quem a usa. A própria docstring de
`73b9847` mostra isso: ela diz que a consulta serve ao `criar_anuncio`, que nunca a chamou.
O cliente real apareceu só no dia seguinte, em outro agregado.

**Problema concreto.**

- **O Pedido ganha acesso de escrita à Venda.** Pela regra de agregados do livro-texto, cada caso de uso
  altera um agregado só. O `criar_pedido` precisa apenas *ler* o preço do anúncio ativo,
  mas a assinatura entrega um objeto com `add()`. Nada no tipo impede que uma mudança
  futura no service do Pedido grave ou altere vendas, misturando dois agregados na mesma
  operação sem que ninguém perceba na revisão.
- **Uma mudança de requisito plausível obrigaria a violar o LSP.** Imagine que a tela de
  compra passe a mostrar o preço do anúncio ativo antes do pedido, lido de uma fonte só de
  leitura (uma réplica do banco ou um cache de anúncios), para não carregar a sessão
  principal. Essa fonte só sabe responder `get_ativa_por_ticket()`. Para entregá-la ao
  `criar_pedido`, ela teria de herdar da `AbstractVendaRepository` e implementar `add()` e
  `get()`, e a única implementação honesta de `add()` numa fonte só de leitura é lançar
  `NotImplementedError`. Seria uma subclasse que não substitui a base, que é exatamente o
  que o LSP proíbe. A interface larga força o erro em quem estende o sistema.
- **Os testes do Pedido montam mais do que o service usa.** Os cinco testes de
  `criar_pedido` em `tests/unit/test_services_pedido.py` usam o `FakeVendaRepository`
  completo e chamam `add()` só para preparar o cenário. Um teste que quisesse um dublê
  mínimo, com apenas a consulta, não conseguiria: o `abc` recusa instanciar uma
  `AbstractVendaRepository` sem `add()` e `get()`.

### Depois

<!--
Responsável: Miguel
O enunciado exige:
- o hash do commit da refatoração (do próprio autor);
- o que mudou;
- como os testes garantiram que o comportamento não mudou;
- o custo da mudança e por que compensa.
-->

## Guilherme — OCP

### Antes

<!--
Responsável: Guilherme
O enunciado exige:
- o princípio violado;
- o trecho do código;
- o hash do commit anterior a 06/10;
- o problema concreto que a violação causa.
-->

### Depois

<!--
Responsável: Guilherme
O enunciado exige:
- o hash do commit da refatoração (do próprio autor);
- o que mudou;
- como os testes garantiram que o comportamento não mudou;
- o custo da mudança e por que compensa.
-->
