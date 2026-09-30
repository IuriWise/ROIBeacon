import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from analytics import DataError, assess, brl, prepare, report, simulate
from integrations import explain, save_sheet, failure_message
from scenarios import SCENARIOS, load_scenario

load_dotenv()
st.set_page_config(page_title='ROIBeacon | Growth Analytics', page_icon='📊', layout='wide')


def setting(name):
    if os.getenv(name):
        return os.getenv(name)
    try:
        return st.secrets.get(name)
    except (FileNotFoundError, ValueError):
        return None


def analyze(frame, name, narrative=''):
    rows = prepare(frame)
    evaluation = assess(rows)
    st.session_state['analysis'] = {'rows': rows, 'evaluation': evaluation, 'name': name,
                                    'narrative': narrative, 'ai': '', 'saved': False,
                                    'report': report(rows, evaluation)}


def delta(value, reference):
    return ('-' if value < 0 else '+') + brl(abs(value)) + reference


st.title('📊 ROIBeacon')
st.write('Entenda o retorno do cashback antes de decidir escalar um teste.')
st.caption('Os números são calculados pelo sistema; a IA, quando solicitada, interpreta os resultados.')

with st.container(border=True):
    st.subheader('Explore uma decisão em poucos cliques')
    scenario = st.selectbox('Cenário fictício', list(SCENARIOS), key='scenario')
    if st.button('Experimentar com dados de exemplo', type='primary', key='demo'):
        frame, narrative = load_scenario(scenario)
        analyze(frame, scenario, narrative)
    st.caption('Sem cadastro ou credenciais. Dados fictícios e interpretação pré-gerada, sem chamada à IA.')

with st.expander('Analisar meu CSV'):
    st.write('Uma linha por variante. Obrigatórias: grupo, vendas, comissao, cashback. Opcionais: usuarios e compradores únicos.')
    st.caption('Valores: 1234.56 ou "R$ 1.234,56". Receita é ambígua e não substitui comissão. A primeira linha é o controle. Máximo: 2 MB e 20 variantes.')
    upload = st.file_uploader('Arquivo CSV', type=['csv'])
    if st.button('Calcular métricas', key='calculate'):
        st.session_state.pop('analysis', None)
        if upload is None:
            st.warning('Selecione um CSV para continuar.')
        elif upload.size > 2_000_000:
            st.error('O arquivo excede o limite de 2 MB.')
        else:
            try:
                analyze(pd.read_csv(upload, sep=None, engine='python', dtype=str, keep_default_na=False), upload.name)
            except DataError as exc:
                st.error(str(exc))
            except Exception:
                st.error('Não foi possível ler o CSV. Confira a codificação UTF-8, o separador e o cabeçalho.')
    st.download_button('Baixar CSV de exemplo', load_scenario(scenario)[0].to_csv(index=False), 'exemplo.csv', 'text/csv', key='sample_csv')

result = st.session_state.get('analysis')
if result:
    rows, evaluation = result['rows'], result['evaluation']
    st.divider()
    st.subheader('Resultado da análise')
    st.caption('Fonte: ' + result['name'])
    if result['narrative']:
        st.info('DEMONSTRAÇÃO · Dados fictícios. Interpretação pré-gerada; métricas recalculadas em Python.')
    selected = st.selectbox('Variante nos cartões', range(len(rows)), format_func=lambda i: rows[i]['grupo'], key='variant_'+result['name'])
    row, baseline = rows[selected], rows[0]
    columns = st.columns(3)
    for column, label, key in zip(columns, ['Comissão', 'Cashback', 'Resultado líquido'], ['comissao', 'cashback', 'liquido']):
        difference = row[key] - baseline[key]
        column.metric(label, brl(row[key]), delta(difference, ' vs. controle'), delta_color='inverse' if key == 'cashback' else 'normal')
    st.caption('Resultado líquido parcial, antes de custos operacionais e tributos. Comparações de totais dependem do tamanho dos grupos.')
    table = pd.DataFrame([{k: float(v) if k in ['comissao', 'cashback', 'liquido'] else v for k, v in r.items() if k in ['grupo', 'comissao', 'cashback', 'liquido']} for r in rows]).set_index('grupo')
    st.bar_chart(table, stack=False, y_label='Valor (R$)')
    st.warning(evaluation['status'])
    st.markdown(result['report'].replace('$', r'\$'))
    if evaluation['intervals']:
        with st.expander('Incerteza e tamanho dos grupos', expanded=True):
            st.dataframe(pd.DataFrame([{'Variante': x['grupo'], 'Conversão': f"{x['conversao']:.2%}", 'IC 95% inferior (Wilson)': f"{x['inferior']:.2%}", 'IC 95% superior (Wilson)': f"{x['superior']:.2%}"} for x in evaluation['intervals']]), hide_index=True)
            if evaluation['difference']:
                lo, hi = evaluation['difference']
                st.write(f'Diferença de conversão (segunda variante − controle), IC 95% aproximado: {lo*100:.2f} a {hi*100:.2f} pontos percentuais.')
            st.caption('Hipóteses: usuários independentes, grupos exclusivos e uma conversão por usuário. Intervalos exploratórios; não corrigem consultas repetidas nem comprovam ganho financeiro.')
    if result['narrative']:
        st.subheader('Interpretação pré-gerada')
        st.write(result['narrative'].replace('$', r'\$'))
    with st.expander('Explicação complementar com IA (opcional)'):
        instruction = st.text_area('Diretriz de análise', 'Explique os ganhos, os riscos e o que falta para decidir.', max_chars=2000)
        st.caption('Ao gerar, métricas agregadas, nomes dos grupos e diretriz serão enviados à Groq. Não inclua dados pessoais.')
        if st.button('Gerar explicação com IA', key='explain'):
            key = setting('GROQ_API_KEY')
            if not key:
                st.info('Configure GROQ_API_KEY para usar IA. A análise local já está disponível.')
            else:
                try:
                    with st.spinner('Gerando explicação...'):
                        result['ai'] = explain(key, rows, evaluation, instruction)
                        result['saved'] = False
                except Exception as exc:
                    st.warning(failure_message('groq', exc) + ' As métricas e o relatório local continuam disponíveis.')
        if result['ai']:
            st.caption('Texto gerado por IA; revise a interpretação. A decisão e os números oficiais são os calculados acima.')
            st.write(result['ai'].replace('$', r'\$'))
    full_report = result['report']
    if result['narrative']:
        full_report += '\n\n## Demonstração fictícia — interpretação pré-gerada\n' + result['narrative']
    if result['ai']:
        full_report += '\n\n## Explicação complementar por IA\n' + result['ai']
    st.download_button('Baixar relatório (.md)', full_report, 'relatorio_roibeacon.md', 'text/markdown', key='download')
    if st.button('Salvar no Google Sheets (opcional)', key='save', disabled=result['saved']):
        sheet_id, credentials = setting('GOOGLE_SHEETS_ID'), setting('gcp_service_account')
        if not sheet_id or not credentials:
            st.info('Configure GOOGLE_SHEETS_ID e gcp_service_account para salvar. O relatório continua disponível para download.')
        else:
            try:
                save_sheet(sheet_id, credentials, result['name'], full_report)
                result['saved'] = True
                st.rerun()
            except Exception as exc:
                st.warning(failure_message('sheets', exc) + ' Sua análise foi preservada; você pode baixar o relatório.')
    if result['saved']:
        st.success('Relatório salvo no Google Sheets.')
    with st.container(border=True):
        st.subheader('Simulador de cashback')
        st.write('Hipótese: volume de vendas constante. As taxas incidem sobre vendas. Não estimamos mudanças de conversão ou demanda.')
        sales = st.number_input('Vendas projetadas (R$)', min_value=0.0, max_value=1e12, value=float(row['vendas']), key='sales_'+result['name']+str(selected))
        commission_rate = st.slider('Comissão sobre vendas (%)', 0.0, 100.0, float(row['comissao']/row['vendas']*100), .1, key='commission_'+result['name']+str(selected))
        cashback_rate = st.slider('Cashback sobre vendas (%)', 0.0, 100.0, min(100.0, float(row['cashback']/row['vendas']*100)), .1, key='cashback_'+result['name']+str(selected))
        commission, cashback, net = simulate(sales, commission_rate, cashback_rate)
        st.metric('Resultado líquido projetado', brl(net), delta(net-row['liquido'], ' vs. observado'))
        st.caption(f'Comissão projetada: {brl(commission)} · Cashback projetado: {brl(cashback)}. Outros custos e tributos não incluídos.'.replace('$', r'\$'))
else:
    st.info('Escolha um cenário e clique em “Experimentar com dados de exemplo”, ou envie seu CSV.')
