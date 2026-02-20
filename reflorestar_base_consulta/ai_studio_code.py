import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import os
from PIL import Image

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Seagri - Reflorestar", layout="wide", page_icon="🌳")

# 2. CSS PARA CORRIGIR VISUALIZAÇÃO (TEMA CLARO/ESCURO)
st.markdown("""
    <style>
    /* Fundo da barra lateral */
    [data-testid="stSidebar"] {
        background-color: #0066b3 !important;
    }
    /* Estilo para labels e inputs na barra lateral */
    [data-testid="stSidebar"] label {
        color: white !important;
        font-weight: bold !important;
    }
    [data-testid="stSidebar"] input {
        color: #1a1a1a !important;
        background-color: #ffffff !important;
        border: 2px solid #f39200 !important;
    }
    /* Texto dos botões e mensagens de erro na sidebar */
    .stSidebar .stMarkdown p {
        color: white !important;
    }
    
    /* Cores Seagri no corpo do app */
    h1, h2, h3 { color: #0066b3 !important; }
    
    /* Expander de resultados */
    .stExpander {
        border: 2px solid #f39200 !important;
        background-color: #f8f9fa !important;
        color: black !important;
    }
    .stExpander * { color: black !important; }
    
    /* Ajuste para o Processo SEI ficar visível */
    .sei-style {
        color: #2e7d32 !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. FUNÇÃO DE CARREGAMENTO COM LIMPEZA DE COLUNAS
@st.cache_data
def carregar_dados():
    def ler_csv(nome):
        for root, dirs, files in os.walk("."):
            if nome in files:
                path = os.path.join(root, nome)
                df = pd.read_csv(path, dtype=str).fillna("")
                # LIMPEZA CRÍTICA: remove espaços extras dos nomes das colunas
                df.columns = df.columns.str.strip()
                return df
        return pd.DataFrame()
    
    return ler_csv('cadastro_beneficiarios.csv'), \
           ler_csv('cadastro_unidades.csv'), \
           ler_csv('cadastro_doacoes.csv'), \
           ler_csv('cadastro_seagri_interno.csv')

df_ben, df_und, df_doa, df_int = carregar_dados()

# 4. AUTENTICAÇÃO
st.sidebar.markdown("## 🔐 Acesso ao Sistema")
with st.sidebar.container():
    u_email = st.text_input("E-mail corporativo").strip().lower()
    u_fone = st.text_input("Telefone (ex: 61981591367)").strip()
    
    acesso_total = False
    if u_email and u_fone:
        # Limpa o fone digitado e o fone do banco para comparar apenas números
        u_fone_limpo = re.sub(r'\D', '', u_fone)
        
        if not df_int.empty:
            # Compara e-mail e fone (limpando espaços e caracteres especiais)
            valido = df_int[
                (df_int['Email'].str.strip().str.lower() == u_email) & 
                (df_int['Fone'].str.replace(r'\D', '', regex=True) == u_fone_limpo)
            ]
            
            if not valido.empty:
                st.sidebar.success("✅ Acesso Total Autorizado")
                acesso_total = True
            else:
                st.sidebar.error("❌ Dados não conferem.")
        else:
            st.sidebar.error("⚠️ Base de usuários não encontrada.")

# 5. LOGO E TÍTULO
logo_path = "logo_seagri.png"
# Busca logo se estiver em subpasta
for root, dirs, files in os.walk("."):
    if "logo_seagri.png" in files:
        logo_path = os.path.join(root, "logo_seagri.png")
        break

c_l, c_t = st.columns([1, 4])
with c_l:
    if os.path.exists(logo_path): st.image(logo_path, width=150)
with c_t:
    st.title("Sistema Reflorestar - SEAGRI-DF")
    status = "🔓 TOTAL" if acesso_total else "🔒 RESTRITO (Público)"
    st.write(f"Nível de Acesso: **{status}**")

# 6. FILTROS DE BUSCA
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔎 Filtrar Dados")
busca = st.sidebar.text_input("Nome, CPF, CAR ou Telefone")

# 7. LÓGICA DE EXIBIÇÃO
if not df_ben.empty:
    res = df_ben.copy()
    
    if busca:
        b_limpa = re.sub(r'\D', '', busca)
        res = res[
            res['Nome'].str.contains(busca, case=False) |
            res['Código do CAR'].str.contains(busca, case=False) |
            res['CPF'].str.replace(r'\D', '', regex=True).str.contains(b_limpa if b_limpa else "XXXXX") |
            res['Fone 1'].str.replace(r'\D', '', regex=True).str.contains(b_limpa if b_limpa else "XXXXX")
        ]

    if busca:
        for _, ben in res.iterrows():
            with st.expander(f"👤 {ben['Nome'].upper()}", expanded=True):
                # Dados sensíveis ocultos se não for usuário interno
                cpf_val = ben['CPF'] if acesso_total else "🔒 Oculto (Faça Login)"
                fone_val = ben['Fone 1'] if acesso_total else "🔒 Oculto (Faça Login)"
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**CPF/CNPJ:** {cpf_val}")
                    st.write(f"**Área:** {ben['Tamanho da propriedade (ha)']} ha")
                with col2:
                    st.markdown(f"**Processo SEI:** <span class='sei-style'>{ben['N° Processo SEI']}</span>", unsafe_allow_html=True)
                    st.write(f"**Localidade:** {ben['IDLocalidade']}")
                with col3:
                    st.write(f"**Telefone:** {fone_val}")
                    st.write(f"**CAR:** {ben['Código do CAR']}")

                # Unidades e Doações
                unds = df_und[df_und['Beneficiário'] == ben['Nome']]
                if not unds.empty:
                    st.markdown("---")
                    for _, u in unds.iterrows():
                        st.markdown(f"📍 **Unidade {u['ID und reabilitação']}** - *{u['Tipo de Und']}*")
                        doas = df_doa[df_doa['ID Und Reab'] == u['ID und reabilitação']]
                        if not doas.empty:
                            st.dataframe(doas[['Data', 'SomaDequant', 'Política Pública', 'Origem das mudas']], hide_index=True)
                else:
                    st.info("Nenhuma unidade vinculada.")

    else:
        # Dashboard Inicial
        st.markdown("### 📊 Estatísticas Gerais")
        m1, m2, m3 = st.columns(3)
        m1.metric("Beneficiários", len(df_ben))
        m_total = pd.to_numeric(df_doa['SomaDequant'], errors='coerce').sum()
        m2.metric("Mudas Doadas", f"{int(m_total):,}")
        m3.metric("Unidades de Plantio", len(df_und))
        st.info("Digite um nome ou documento na barra lateral para detalhar a consulta.")
else:
    st.error("Erro ao carregar base de dados. Verifique os arquivos CSV.")
