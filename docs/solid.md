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

### Depois

<!--
Responsável: Caio
O enunciado exige:
- o hash do commit da refatoração (do próprio autor);
- o que mudou;
- como os testes garantiram que o comportamento não mudou;
- o custo da mudança e por que compensa.
-->

## Igor — a definir

### Antes

<!--
Responsável: Igor
O enunciado exige:
- o princípio violado;
- o trecho do código;
- o hash do commit anterior a 06/10;
- o problema concreto que a violação causa.
-->

### Depois

<!--
Responsável: Igor
O enunciado exige:
- o hash do commit da refatoração (do próprio autor);
- o que mudou;
- como os testes garantiram que o comportamento não mudou;
- o custo da mudança e por que compensa.
-->

## Miguel — a definir

### Antes

<!--
Responsável: Miguel
O enunciado exige:
- o princípio violado;
- o trecho do código;
- o hash do commit anterior a 06/10;
- o problema concreto que a violação causa.
-->

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
