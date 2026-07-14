import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
import gspread
from google.oauth2.service_account import Credentials

if os.path.exists(".env"):
    load_dotenv()

chave_api = os.getenv("GROQ_API_KEY")

client = Groq(api_key=chave_api)

def limpar_moeda(valor):
    """Remove símbolos monetários e formatação brasileira para conversão em float."""
    if isinstance(valor, str):
        valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(valor)
    except:
        return 0.0

st.set_page_config(page_title="Méliuz - AI Growth Analytics", page_icon="📊", layout="wide")

st.title("📊 AI Growth Analytics")
st.write("Plataforma automatizada para análise profunda de Testes A/B e Otimização de Margem de Cashback.")
st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Entrada de Dados")
    arquivo_subido = st.file_uploader("Selecione o arquivo CSV do Teste A/B", type="csv")
    
    st.subheader("Contexto Estratégico")
    prompt_usuario = st.text_area(
        "Diretriz de Análise do Negócio:",
        placeholder="Ex: Avalie qual variante trouxe o melhor ROI considerando o custo de cashback versus a comissão retida, e decida o plano de escala.",
        height=150
    )
    
    botao_executar = st.button("Fazer Análise ", use_container_width=True)

with col2:
    st.subheader("📑 Relatório e Tomada de Decisão")
    
    if botao_executar:
        if not arquivo_subido:
            st.warning("Por favor, faça o upload de um arquivo CSV válido antes de prosseguir.")
        elif not prompt_usuario.strip():
            st.warning("Insira uma diretriz ou pergunta estratégica para orientar a IA.")
        else:
            with st.spinner("Processando volumetria de dados e consultando modelos sêniores..."):
                try:
                    df = pd.read_csv(arquivo_subido)
                    
                    colunas_criticas = ['comissão', 'cashback', 'vendas totais', 'receita', 'faturamento']
                    for col in df.columns:
                        if col.lower() in colunas_criticas or any(c in col.lower() for c in colunas_criticas):
                            df[col] = df[col].apply(limpar_moeda)
                    
                    coluna_grupo = 'Grupos de usuários'
                    if coluna_grupo in df.columns:
                        df_consolidado = df.groupby(coluna_grupo).sum(numeric_only=True)
                        dados_finais_texto = df_consolidado.to_string()
                    else:
                        dados_finais_texto = df.to_string()
                    
                    resposta_ia = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Você é um Analista de Growth Sênior da Méliuz, especialista em testes A/B e economia de plataformas de cashback. "
                                    "Seu escopo de atuação é EXCLUSIVAMENTE os dados numéricos e textuais contidos no arquivo fornecido pelo usuário. "
                                    "Se o usuário fizer qualquer tipo de pergunta fora deste contexto analítico empresarial — incluindo, mas não se limitando a: "
                                    "previsão do tempo, condições climáticas, fofocas, receitas, códigos de outros sistemas ou conversas cotidianas —, você deve "
                                    "bloquear a resposta imediatamente. "
                                    "Caso ocorra um desvio de escopo, responda de forma extremamente curta, formal e educada no máximo em 200 caracteres, explicando que suas funções são "
                                    "restritas à auditoria e análise de dados de Growth da Méliuz."
                                )
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Analise os dados estruturados do seguinte teste A/B:\n\n{dados_finais_texto}\n\n"
                                    f"Com base nesses números, atenda à seguinte demanda do time de negócio: {prompt_usuario}\n\n"
                                    "Gere um relatório executivo fundamentado em dados financeiros reais (ROI, margem de comissão líquida). "
                                    "Conclua indicando explicitamente qual variante deve receber 100% do tráfego."
                                )
                            }
                        ]
                    )
                    texto_limpo = resposta_ia.choices[0].message.content if resposta_ia.choices else ""
                    st.success("Análise concluída com sucesso! Enviando para o banco de dados...")

                    escopos = [
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/drive"
                        ]

                    credenciais_dict = dict(st.secrets["gcp_service_account"])
                    credenciais = Credentials.from_service_account_info(credenciais_dict, scopes=escopos)
                        
                    cliente_google = gspread.authorize(credenciais)

                    ID_DA_PLANILHA = "1ocVlzJ7Gyk3RxS7hSXLS7aERve95XdnpNS1wv_rZ5SI"
                    planilha = cliente_google.open_by_key(ID_DA_PLANILHA).sheet1

                    nova_linha = [
                        arquivo_subido.name,
                        "Auditoria automatizada de margem e conversão do teste A/B",
                        texto_limpo,
                    ]
                    planilha.append_row(nova_linha)

                    st.success("✅ Teste registrado com sucesso na planilha oficial!") 
                except Exception as e:
                    st.error(f"Falha crítica na execução ou na comunicação com a API: {e}")
    else:
        st.info("Aguardando o upload dos dados e o acionamento do botão para gerar a análise.")
