# ROIBeacon | Automação de Testes A/B -  Méliuz Growth

**Teste Técnico: Estágio de Growth AI-Native**

![Demonstração do Sistema](assets/demo.gif)

Olá! Este é o repositório da minha solução para o desafio de automação de análises de testes A/B de cashback. 

O objetivo deste projeto é eliminar o trabalho manual e repetitivo da equipe de Growth, processando os datasets dos testes e decidindo, de forma rápida e embasada em dados reais (ROI e Margem), qual variante deve ser escalada para 100% do tráfego.

## Como o sistema funciona?

Para resolver esse problema, construí um fluxo de trabalho (pipeline) focado em eficiência e usabilidade. Qualquer pessoa do time pode usar a ferramenta seguindo esta jornada:

1. **Upload Simples:** Uma interface limpa onde o usuário envia o arquivo `.csv` do parceiro (A, B ou C) sem precisar alterar nenhuma linha de código.
2. **Tratamento de Dados (Sanitization):** Embaixo dos panos, o sistema usa a biblioteca Pandas para limpar os dados financeiros (removendo símbolos de "R$" e ajustando as vírgulas), transformando texto em números exatos para o cálculo.
3. **Motor de Decisão (IA):** O dataset limpo é enviado para uma Inteligência Artificial de ponta (modelo Llama 3.3 70B via Groq API). A IA atua como um analista de Growth: ela calcula as margens, o custo do cashback, o ROI e entrega um relatório executivo apontando o grupo vencedor.
4. **Registro Automático na Nuvem:** Ao finalizar a análise, a aplicação se conecta diretamente à API do Google Workspace e escreve o resultado em uma planilha do Google Sheets, mantendo o histórico de todos os testes organizados e centralizados de forma autônoma.

## Stack

Escolhi ferramentas modernas, fáceis de manter e muito utilizadas no mercado de dados e IA:

* **Python:** Linguagem principal do projeto.
* **Streamlit:** Escolhido para construir a interface web rapidamente, permitindo focar 100% na regra de negócio e na solução do problema.
* **Pandas:** Para manipulação, limpeza e estruturação confiável das tabelas.
* **Groq API (Llama 3.3 70B):** Selecionado pela velocidade altíssima de resposta e excelente raciocínio lógico-matemático.
* **gspread & Google Auth:** Bibliotecas para realizar a integração autônoma com o banco de dados final (Google Sheets API).

## 🔗 Links da Entrega

* 🌐 **Aplicação:** [Acessar o ROIBeacon](https://roibeacon-meliuz.streamlit.app/)
* 📊 **Planilha de Acompanhamento (Sheets):** [Ver no Google Sheets](https://docs.google.com/spreadsheets/d/1ocVlzJ7Gyk3RxS7hSXLS7aERve95XdnpNS1wv_rZ5SI/edit?usp=sharing)
* 📄 **Relatórios Individuais:** Os relatórios brutos gerados pela IA estão na pasta `/relatorios` deste repositório para conferência.

---

## Como rodar localmente

### Pré-requisitos

* Python 3.10 ou superior
* Uma chave de API da [Groq](https://console.groq.com/)
* Uma Service Account do Google Cloud com acesso à API do Google Sheets

### 1. Clone o repositório

```bash
git clone https://github.com/IuriWise/roibeacon-meliuz.git
cd roibeacon-meliuz
```

### 2. Crie e ative um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as Credenciais (Secrets)

Crie uma pasta `.streamlit` na raiz do projeto e um arquivo `secrets.toml` dentro dela com:

```toml
GROQ_API_KEY = "sua_chave_groq_aqui"

[gcp_service_account]
type = "service_account"
project_id = "seu-projeto-id"
private_key = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC3...
-----END PRIVATE KEY-----
"""
client_email = "seu-bot@seu-projeto.iam.gserviceaccount.com"
```

### 5. Rode a aplicação

```bash
streamlit run app.py
```

A aplicação abrirá automaticamente em `http://localhost:8501`.

### 6. Use a ferramenta

1. Faça upload do CSV de um dos parceiros (A, B ou C).
2. Aguarde o processamento e a análise da IA.
3. Confira o relatório gerado na tela e o registro automático na planilha do Google Sheets.

---

## Estrutura do projeto

```text
roibeacon-meliuz/
├── .streamlit/
│   └── secrets.toml        # Credenciais da Groq e Service Account (não versionado)
├── relatorios/             # Relatórios gerados para os datasets A, B e C
├── .env.example            # Template demonstrativo das variáveis de ambiente
├── app.py                  # Aplicação Streamlit (interface e orquestração do pipeline)
├── requirements.txt        # Dependências do projeto
└── README.md               # Documentação oficial
```

---

Desenvolvido por Iuri Paiva.