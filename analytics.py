"""Cálculos determinísticos para dados agregados por variante."""
from decimal import Decimal, InvalidOperation
import math
import re
import unicodedata

import pandas as pd


class DataError(ValueError):
    """Entrada inválida, com mensagem segura para exibição."""


def money(value):
    """Aceita decimal com ponto ou moeda pt-BR; rejeita ambiguidade e vazios."""
    raw = str(value).strip()
    brazilian = raw.startswith('R$') or ',' in raw
    raw = raw.removeprefix('R$').strip()
    if brazilian:
        if not re.fullmatch(r'[+-]?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,2})?', raw):
            raise DataError('Valor monetário inválido. Use 1234.56 ou "R$ 1.234,56".')
        raw = raw.replace('.', '').replace(',', '.')
    elif not re.fullmatch(r'[+-]?\d+(?:\.\d{1,2})?', raw):
        raise DataError('Valor monetário inválido ou ambíguo. Use 1234.56 ou "R$ 1.234,56".')
    try:
        result = Decimal(raw)
    except InvalidOperation as exc:
        raise DataError('Valor monetário inválido.') from exc
    if not result.is_finite() or result < 0 or result > Decimal('1000000000000'):
        raise DataError('Valores monetários devem estar entre zero e 1 trilhão.')
    return result.quantize(Decimal('0.01'))


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text).strip().lower())
                   if not unicodedata.combining(c))


ALIASES = {
    'grupo': 'grupo', 'grupos de usuarios': 'grupo', 'variante': 'grupo',
    'comissao': 'comissao', 'cashback': 'cashback', 'vendas totais': 'vendas',
    'vendas': 'vendas', 'faturamento': 'vendas', 'usuarios': 'usuarios',
    'compradores': 'compradores',
}


def prepare(frame):
    if frame.empty or len(frame) > 20:
        raise DataError('Envie de 1 a 20 linhas, uma por variante.')
    rename = {c: ALIASES[normalized(c)] for c in frame if normalized(c) in ALIASES}
    if len(set(rename.values())) != len(rename):
        raise DataError('Há colunas duplicadas para a mesma métrica.')
    data = frame.rename(columns=rename)
    required = {'grupo', 'comissao', 'cashback', 'vendas'}
    if not required.issubset(data.columns):
        raise DataError('Colunas obrigatórias: grupo, comissao, cashback e vendas. Receita não é convertida automaticamente em comissão ou vendas.')
    rows = []
    for position, (_, row) in enumerate(data.iterrows(), 2):
        group = str(row['grupo']).strip()
        if not group or len(group) > 80 or pd.isna(row['grupo']):
            raise DataError(f'Linha {position}: informe um grupo com até 80 caracteres.')
        record = {'grupo': group}
        for column in ['comissao', 'cashback', 'vendas']:
            try:
                record[column] = money(row[column])
            except DataError as exc:
                raise DataError(f'Linha {position}, coluna {column}: {exc}') from exc
        if record['vendas'] <= 0 or record['comissao'] > record['vendas']:
            raise DataError(f'Linha {position}: vendas devem ser positivas e comissão não pode exceder vendas.')
        for column in ['usuarios', 'compradores']:
            if column in data:
                value = str(row[column]).strip()
                if not re.fullmatch(r'\d+', value) or int(value) > 10**12:
                    raise DataError(f'Linha {position}: {column} deve ser um inteiro não negativo, até 1 trilhão.')
                record[column] = int(value)
        if 'usuarios' in record and record['usuarios'] == 0:
            raise DataError(f'Linha {position}: usuarios deve ser maior que zero.')
        if {'usuarios', 'compradores'}.issubset(record) and record['compradores'] > record['usuarios']:
            raise DataError(f'Linha {position}: compradores não pode exceder usuarios.')
        record['liquido'] = record['comissao'] - record['cashback']
        record['margem'] = float(record['liquido'] / record['vendas'])
        record['roi'] = float(record['liquido'] / record['cashback']) if record['cashback'] else None
        record['liquido_usuario'] = float(record['liquido'] / record['usuarios']) if record.get('usuarios') else None
        rows.append(record)
    if len({r['grupo'] for r in rows}) != len(rows):
        raise DataError('Grupos repetidos: envie uma linha agregada por variante, sem somar percentuais ou identificadores.')
    return rows


def wilson(successes, total):
    p, z = successes / total, 1.959963984540054
    denominator = 1 + z*z / total
    center = (p + z*z / (2*total)) / denominator
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / denominator
    return center-half, center+half


def assess(rows):
    notes = []
    intervals = []
    for r in rows:
        if 'usuarios' in r and 'compradores' in r:
            low, high = wilson(r['compradores'], r['usuarios'])
            intervals.append({'grupo': r['grupo'], 'conversao': r['compradores']/r['usuarios'], 'inferior': low, 'superior': high})
    if len(rows) != 2:
        notes.append('A comparação de incerteza exige exatamente duas variantes; múltiplas comparações não são corrigidas neste protótipo.')
    if len(intervals) != len(rows):
        notes.append('Faltam usuarios e/ou compradores: não é possível avaliar conversão, tamanho dos grupos e sua incerteza.')
    difference = None
    if len(rows) == 2 and len(intervals) == 2:
        a, b = rows
        if min(a['usuarios'], b['usuarios']) / max(a['usuarios'], b['usuarios']) < .8:
            notes.append('Grupos desbalanceados: confirme a alocação planejada e investigue perdas de rastreamento.')
        if any(r['usuarios'] < 100 or min(r['compradores'], r['usuarios']-r['compradores']) < 5 for r in rows):
            notes.append('Amostra insuficiente para a aproximação usada: mínimo operacional de 100 usuários e 5 compradores/não compradores por grupo. Isso não substitui cálculo de poder.')
        else:
            p0, p1 = (r['compradores']/r['usuarios'] for r in rows)
            error = 1.959963984540054 * math.sqrt(p0*(1-p0)/a['usuarios'] + p1*(1-p1)/b['usuarios'])
            difference = (p1-p0-error, p1-p0+error)
            if difference[0] <= 0 <= difference[1]:
                notes.append('O intervalo aproximado da diferença de conversão inclui zero; não há evidência suficiente de mudança nesta métrica.')
    notes.append('Os totais agregados não permitem estimar a incerteza do resultado financeiro por usuário. Faltam dados individuais ou variância, validação da randomização e duração planejada do teste.')
    return {'status': 'Ainda não podemos decidir pela escala', 'notes': notes, 'intervals': intervals, 'difference': difference}


def brl(value):
    return 'R$ ' + f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def report(rows, assessment):
    lines = ['# Análise financeira do teste', '', '| Variante | Comissão | Cashback | Resultado líquido | Margem | ROI |', '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        roi = f"{r['roi']:.1%}" if r['roi'] is not None else 'Indefinido (cashback zero)'
        group = r['grupo'].replace('|', '/').replace('\n', ' ')
        lines.append(f"| {group} | {brl(r['comissao'])} | {brl(r['cashback'])} | {brl(r['liquido'])} | {r['margem']:.1%} | {roi} |")
    lines += ['', '## Tamanho dos grupos e resultado por usuário']
    for r in rows:
        if r.get('usuarios'):
            lines.append(f"- {r['grupo']}: {r['usuarios']} usuários expostos; resultado líquido por usuário: {brl(r['liquido_usuario'])}.")
        else:
            lines.append(f"- {r['grupo']}: número de usuários não informado.")
    if assessment['intervals']:
        lines += ['', '## Incerteza de conversão (exploratória)']
        for interval in assessment['intervals']:
            lines.append(f"- {interval['grupo']}: conversão {interval['conversao']:.2%}; IC 95% de Wilson: {interval['inferior']:.2%} a {interval['superior']:.2%}.")
        if assessment['difference']:
            low, high = assessment['difference']
            lines.append(f'Diferença de conversão (segunda variante − controle), IC 95% aproximado: {low*100:.2f} a {high*100:.2f} pontos percentuais.')
        lines.append('Hipóteses: usuários independentes, grupos exclusivos e uma compra por usuário. Sem correção para múltiplas comparações ou consultas repetidas.')
    lines += ['', '## Decisão', assessment['status'], *['- '+n for n in assessment['notes']], '', 'Resultado líquido = comissão − cashback, antes de outros custos e tributos. Margem = resultado líquido / vendas. ROI = resultado líquido / cashback. Intervalos de conversão não provam rentabilidade.']
    return '\n'.join(lines)


def simulate(sales, commission_rate, cashback_rate):
    if not all(math.isfinite(float(v)) for v in [sales, commission_rate, cashback_rate]):
        raise DataError('Premissas devem ser finitas.')
    if sales < 0 or not 0 <= commission_rate <= 100 or not 0 <= cashback_rate <= 100:
        raise DataError('Vendas devem ser não negativas e taxas entre 0 e 100%.')
    commission = (Decimal(str(sales))*Decimal(str(commission_rate))/100).quantize(Decimal('.01'))
    cashback = (Decimal(str(sales))*Decimal(str(cashback_rate))/100).quantize(Decimal('.01'))
    return commission, cashback, commission-cashback
