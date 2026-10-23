# ADR 0001 — Mapeamento ORM imperativo

- **Status:** Aceita
- **Data:** 2026-10-22
- **Autor:** Lucas Esteves (@LucasEsteves29)

## Contexto

O RocketTicket persiste os agregados Ticket, Venda e Pedido (com o Pagamento) usando o
SQLAlchemy 2.0. As regras de negócio ficam em `domain/model.py`: o ciclo de vida do
Ticket, o teto de 110% da Venda e a confirmação do Pedido. Seguindo o Cosmic Python, o
domínio deveria depender só da biblioteca padrão, para ser testado sem banco e sem
framework. Faltava decidir como ligar essas classes às tabelas sem que elas passassem a
depender do ORM.

## Decisão

Usamos o mapeamento imperativo do SQLAlchemy. As tabelas são declaradas em
`adapters/orm.py` e ligadas às classes do domínio com `registry.map_imperatively`, numa
função `_mapear_<agregado>()` por agregado, todas chamadas por `start_mappers()`. O
`model.py` não importa SQLAlchemy: a dependência vai de `adapters/` para `domain/`,
nunca ao contrário.

## Alternativas

- **Mapeamento declarativo**: as classes do domínio herdariam de uma base declarativa,
  com as colunas na própria classe. Descartado porque o domínio passaria a depender do
  ORM: o `model.py` importaria SQLAlchemy, e testar uma regra de negócio exigiria o
  mapeamento carregado.
- **SQL manual no repositório**, sem ORM: o domínio continuaria puro, mas cada
  repositório faria à mão a conversão de objeto para linha e de linha para objeto,
  incluindo os status (Enum) e os valores em dinheiro (Decimal). Com o mapeamento
  imperativo, essa conversão fica nos tipos das colunas: `_enum_por_valor()` para os
  status e `Numeric(10, 2)` para dinheiro.

## Consequências

Positivas:
- O domínio é puro: o `model.py` importa só `decimal` e `enum`.
- Os testes unitários rodam sem banco, usando os Fakes dos repositórios.

Negativas:
- Classe e tabela precisam ser mantidas em sincronia: um atributo novo no domínio exige
  a coluna correspondente em `orm.py`.
- `start_mappers()` só pode rodar uma vez por processo. Nos testes, toda fixture que
  mapeia as classes precisa desfazer o mapeamento com `clear_mappers()`.
- Ao ler do banco, o SQLAlchemy recria o objeto sem chamar `__init__`, então as
  invariantes validadas no construtor não são checadas de novo. Foi isso que expôs o
  bug do teto de 110%: com valor original 99,99, o teto exato é 109,989, e um preço
  aceito por esse teto podia ser gravado como 109,99 pelo `Numeric(10, 2)` e voltar do
  banco acima do limite, sem nenhum erro. A correção, com o teto arredondado para baixo
  em `_validar_preco()`, é o assunto do ADR 0003.
