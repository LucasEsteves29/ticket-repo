# Refatorações SOLID — RocketTicket

## Igor Leal (@igorbleal)

### 1. Princípio violado
Princípio violado: SRP (Single Responsibility Principle / Princípio da Responsabilidade Única), com impacto direto também no OCP (Open-Closed Principle).\
Módulo/Agregado: Bloco do agregado Venda em src/rocketicket/domain/model.py e caso de uso criar_anuncio em src/rocketicket/service_layer/services.py.\
Hashes do código "antes": 331685a (24/09/2026, implementação de validar_preco na Venda), 186b52c (26/09/2026) e 38e541d (29/09/2026, implementação de criar_anuncio).\

```python
# src/rocketicket/domain/model.py (estado no commit 331685a / 186b52c)
class Venda:
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
        """Recusa preço acima de 110% do valor original."""
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
        self._validar_preco(novo_preco)
        self.preco = novo_preco
```

### 2. Problema concreto

A entidade Venda acumulava duas responsabilidades distintas (dois motivos para mudar):

Gerenciar o ciclo de vida e a identidade do anúncio de revenda: controlar as transições de estado (ATIVA → CANCELADA ou CONCLUIDA) e garantir que anúncios encerrados não sofram alterações (_exigir_ativa()).\
Calcular e validar a política financeira de teto anti-cambismo: aplicar a fórmula matemática de limite máximo (valor_original * Decimal("1.10")) e a regra de truncamento monetário (quantize(Decimal("0.01"), rounding=ROUND_DOWN)).\

Que mudança ficava difícil:

Se a regra de cálculo do teto mudasse (por exemplo, alteração regulatória do percentual máximo permitido de 110% para 105%, ou um requisito para eventos beneficentes/meia-entrada onde a revenda só pode ocorrer pelo valor facial de 100% sem ágio), seria obrigatório abrir e editar diretamente a classe Venda em model.py.\
Além disso, não era possível reutilizar nem testar o cálculo do limite máximo de revenda isoladamente (por exemplo, para exibir na interface qual é o teto permitido de um ticket antes de o usuário preencher o formulário de anúncio) sem instanciar uma entidade Venda inteira.