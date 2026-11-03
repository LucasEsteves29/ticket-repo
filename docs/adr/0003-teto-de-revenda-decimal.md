# ADR 0003 — Teto de revenda com Decimal arredondado para baixo

- **Status:** Aceita
- **Data:** 2026-10-22 (registra decisão tomada em 24/09/2026, na Fase 1)
- **Autor:** Igor Leal (@igorbleal)

## Contexto

A principal regra anti-cambismo do RocketTicket determina que o preço de revenda
de um ingresso nunca pode ultrapassar 110% do seu valor original (`valor_original`),
tanto na criação do anúncio (`Venda.__init__`) quanto na alteração posterior do
preço (`Venda.alterar_preco()`). Caso o limite seja excedido, o domínio deve
recusar a operação lançando a exceção `PrecoAcimaDoLimite`.

Por se tratar de valores monetários em reais e centavos, o cálculo do teto
(`valor_original * 1.10`) enfrenta dois problemas clássicos de representação e
persistência:
1. O uso de ponto flutuante binário (`float`) introduz imprecisões em frações
   decimais (como `100.00 * 1.10 = 110.00000000000001`), podendo aprovar ou
   rejeitar indevidamente preços exatamente na fronteira do limite.
2. Mesmo com aritmética decimal exata, valores com centavos quebrados geram uma
   terceira casa decimal no produto — por exemplo, `99.99 * 1.10 = 109.989`. No
   banco de dados (`adapters/orm.py`), as colunas monetárias (`preco` e
   `valor_original`) são definidas como `Numeric(10, 2)`. Se o teto exato de
   três casas fosse usado ou arredondado pelo padrão comercial, um preço ou
   limite intermediário como `109.989` seria arredondado para cima pelo banco ao
   ser gravado (virando `109.99`), fazendo a venda persistida superar o teto
   legal de 110% quando recarregada.

## Decisão

Representar todos os valores monetários do sistema (`valor_original`, `preco` e
`valor`) com `decimal.Decimal` da biblioteca padrão e calcular o teto máximo de
revenda no método `Venda._validar_preco()` (`domain/model.py`) truncando o
resultado em duas casas decimais com arredondamento estrito para baixo
(`ROUND_DOWN`):

```python
limite_maximo = (self.valor_original * Decimal("1.10")).quantize(
    Decimal("0.01"), rounding=ROUND_DOWN
)
```

Dessa forma, para um ingresso com `valor_original = Decimal("99.99")`, o cálculo
`99.99 * 1.10 = 109.989` resulta em `limite_maximo = Decimal("109.98")`. Qualquer
valor acima de `109.98` (incluindo `109.985` ou `109.99`) lança
`PrecoAcimaDoLimite`.

Para manter a consistência entre camadas:
- Na camada de adaptação (`adapters/orm.py`), as colunas monetárias usam
  `Numeric(10, 2)` em vez de `Float`.
- Na camada de entrada (`entrypoints/flask_app.py`), os valores monetários são
  recebidos como string no JSON e validados pelo helper `_ler_decimal()`, que
  rejeita números com mais de duas casas decimais (`exponent < -2`) antes de
  chegar ao serviço.

Commits: `cdd0311` (implementação inicial da `Venda`), `331685a` (extração de
`_validar_preco` com `quantize` e `ROUND_DOWN`), `186b52c` (reuso de
`_validar_preco` em `alterar_preco`), `2579d75` (mapeamento `Numeric(10, 2)` na
tabela `vendas`) e `e17c50a` (validação na rota `POST /anuncios`).

## Alternativas

1. **Usar `float` nativo do Python para preços e cálculo do limite.** Rejeitada:
   a representação binária IEEE 754 não representa exatamente frações como `0.10`
   ou `0.01`, gerando erros acumulados de precisão e exigindo comparações com
   tolerância (`math.isclose`) em regras de negócio financeiras.
2. **Comparar `preco <= valor_original * Decimal("1.10")` sem `quantize`.**
   Rejeitada: foi a primeira versão implementada (`cdd0311`), mas permitia
   valores com três casas decimais (como `109.985` para `valor_original = 99.99`)
   no domínio puro que, ao passarem pelo `Numeric(10, 2)` do banco, sofreriam
   arredondamento implícito para `109.99`, violando a invariante de 110% após a
   persistência.
3. **Usar `quantize` com o arredondamento padrão (`ROUND_HALF_EVEN` ou `ROUND_HALF_UP`).**
   Rejeitada: para `valor_original = Decimal("99.99")`, o produto `109.989` seria
   arredondado para `109.99`, que equivale a `110,001%` do valor original —
   portanto acima do teto estrito de 110%.
4. **Armazenar valores monetários em centavos como inteiros (`int`).** Rejeitada:
   embora evite casas decimais no armazenamento, o cálculo de 110% ainda exige
   divisão inteira (`(centavos * 110) // 100`) e transfere para a API, os
   serviços e o ORM a responsabilidade constante de converter entre centavos e
   reais formatados, perdendo a expressividade direta do `Decimal("99.99")`.

## Consequências

**Positivas**
- A invariante de 110% nunca é violada, nem em memória nem após persistir e
  recarregar do banco de dados, pois o teto calculado já nasce com exatamente
  duas casas decimais e nunca excede o limite matemático exato.
- O método privado `_validar_preco()` centraliza a regra em um único ponto na
  entidade `Venda`, garantindo que tanto `__init__()` quanto `alterar_preco()`
  apliquem exatamente o mesmo critério de truncamento.
- Os testes unitários (`tests/unit/test_venda.py`) verificam de forma determinística
  os casos de fronteira: o limite exato truncado (`109.98`), o valor intermediário
  de três casas (`109.985`) e o valor arredondado para cima (`109.99`).

**Negativas**
- O vendedor perde frações de centavo no teto máximo permitido (no caso de
  `R$ 99,99`, os `0,9` décimos de centavo de `109,989` são descartados,
  limitando o anúncio a `R$ 109,98`).
- Toda entrada e saída JSON na API precisa trafegar valores monetários como
  strings (ex.: `"109.98"`) e passar por `_ler_decimal()`, já que o parser JSON
  padrão converteria literais numéricos para `float` antes de construir o
  `Decimal`.

