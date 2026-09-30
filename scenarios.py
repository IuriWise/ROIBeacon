"""Cenários inteiramente fictícios; narrativas pré-geradas, sem uso de IA."""
from pathlib import Path
import pandas as pd

SCENARIOS = {
    'Variante com resultado melhor': ('melhor.csv', 'A variante apresenta resultado líquido observado de R$ 9.500,00, contra R$ 6.000,00 do controle, com o mesmo número de usuários expostos. A conversão também é maior. Próximo passo: validar duração e randomização e coletar a variância financeira antes de escalar.'),
    'Mais vendas, menos margem': ('promocao.csv', 'A promoção aumenta as vendas de R$ 100.000,00 para R$ 150.000,00, mas o cashback reduz o resultado líquido de R$ 6.000,00 para R$ 3.000,00. A margem cai de 6% para 2%. Próximo passo: rever o incentivo; mais vendas não garantem mais rentabilidade.'),
    'Teste inconclusivo': ('inconclusivo.csv', 'O teste tem apenas 40 e 42 usuários, com 4 e 5 compradores. Os valores observados não sustentam uma decisão de escala. Próximo passo: planejar o tamanho da amostra e continuar a coleta sem escolher um vencedor prematuramente.'),
}


def load_scenario(name):
    filename, narrative = SCENARIOS[name]
    return pd.read_csv(Path(__file__).parent / 'examples' / filename, dtype=str), narrative
