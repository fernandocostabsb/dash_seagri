import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import os
from PIL import Image
from fpdf import FPDF
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Seagri - Gestão Reflorestar", layout="wide", page_icon="🌳")

# 2. ESTILIZAÇÃO (CORES SEAGRI E ALTO CONTRASTE)
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #0066b3 !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stTextInput input { color: black !important; background-color: white !important; }
    h1, h2, h3 { color: #0066b3 !important; }
    .stExpander { border: 2px solid #f39200 !important; background-color: #ffffff !important; color: black !important; }
    .stExpander * { color: black !important; }
    .report-box { background-color: #e8f5e9; padding: 15px; border-radius: 10px; border: 1px solid #2e7d32; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 3. CARREGAMENTO DE DADOS
@st.cache_data
def carregar_dados():
    def ler_csv(nome):
        for root, dirs, files in os.walk("."):
            if nome in files:
                df = pd.read_csv(os.path.join(root, nome), dtype=str).fillna("")
                df.columns = df.columns.str.strip()
                return df
        return pd.DataFrame()
    return ler_csv('cadastro_beneficiarios.csv'), ler_csv('cadastro_unidades.csv'), \
           ler_csv('cadastro_doacoes.csv'), ler_csv('cadastro_seagri_interno.csv')

df_ben, df_und, df_doa, df_int = carregar_dados()

# 4. LOGIN / AUTORIZAÇÃO
st.sidebar.markdown("## 🔐 Acesso Interno")
u_email = st.sidebar.text_input("E-mail corporativo").strip().lower()
u_fone = st.sidebar.text_input("Telefone").strip()
acesso_total = False
if u_email and u_fone:
    u_fone_limpo = re.sub(r'\D', '', u_fone)
    if not df_int.empty:
        valido = df_int[(df_int['Email'].str.strip().str.lower() == u_email) & 
                        (df_int['Fone'].str.replace(r'\D', '', regex=True) == u_fone_limpo)]
        if not valido.empty:
            st.sidebar.success("✅ Acesso Autorizado")
            acesso_total = True
        else: st.sidebar.error("❌ Acesso Negado")

# 5. LOGO E TÍTULO
logo_path = "logo_seagri.png"
for root, dirs, files in os.walk("."):
    if "logo_seagri.png" in files: logo_path = os.path.join(root, "logo_seagri.png"); break
c_l, c_t = st.columns([1, 4])
with c_l: 
    if os.path.exists(logo_path): st.image(logo_path, width=150)
with c_t:
    st.title("Sistema Reflorestar - SEAGRI-DF")
    st.write(f"Nível de Acesso: **{'🔓 TOTAL' if acesso_total else '🔒 RESTRITO'}**")

# 6. FILTROS AVANÇADOS NA SIDEBAR
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔎 Filtros de Consulta")

f_texto = st.sidebar.text_input("Nome, CPF, CAR ou Telefone")

# Filtro Localidade / RA
ra_list = sorted(list(set(df_ben['IDLocalidade'].unique())))
f_ra = st.sidebar.selectbox("Região Administrativa / Localidade", ["Todas"] + ra_list)

# Filtro Unidade Hidrográfica
bacia_list = sorted(list(set(df_und['Unidade Hidro'].unique())))
f_bacia = st.sidebar.selectbox("Unidade Hidrográfica", ["Todas"] + bacia_list)

# 7. LÓGICA DE FILTRAGEM
if not df_ben.empty:
    res = df_ben.copy()
    
    # Filtro por Texto
    if f_texto:
        t_limpo = re.sub(r'\D', '', f_texto)
        res = res[res['Nome'].str.contains(f_texto, case=False) | 
                  res['Código do CAR'].str.contains(f_texto, case=False) |
                  res['CPF'].str.replace(r'\D', '', regex=True).str.contains(t_limpo if t_limpo else "NONE") |
                  res['Fone 1'].str.replace(r'\D', '', regex=True).str.contains(t_limpo if t_limpo else "NONE")]

    # Filtro por RA
    if f_ra != "Todas":
        res = res[res['IDLocalidade'] == f_ra]

    # Filtro por Bacia (Busca beneficiários que tenham unidades na bacia X)
    if f_bacia != "Todas":
        nomes_na_bacia = df_und[df_und['Unidade Hidro'] == f_bacia]['Beneficiário'].unique()
        res = res[res['Nome'].isin(nomes_na_bacia)]

    # 8. EXPORTAÇÃO E RELATÓRIO
    if f_texto or f_ra != "Todas" or f_bacia != "Todas":
        st.markdown(f"**{len(res)}** resultados encontrados.")
        
        # Preparar dados para exportação
        df_export = res.copy()
        if not acesso_total:
            df_export['CPF'] = "PROTEGIDO"
            df_export['Fone 1'] = "PROTEGIDO"
            df_export['Fone 2'] = "PROTEGIDO"

        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Relatório CSV", csv, "relatorio_seagri.csv", "text/csv")
        
        # 9. EXIBIÇÃO DOS CARDS
        for _, ben in res.iterrows():
            with st.expander(f"👤 {ben['Nome'].upper()}", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**CPF/CNPJ:** {ben['CPF'] if acesso_total else '🔒'}")
                    st.write(f"**Área:** {ben['Tamanho da propriedade (ha)']} ha")
                with c2:
                    st.write(f"**Processo SEI:** {ben['N° Processo SEI']}")
                    st.write(f"**Localidade:** {ben['IDLocalidade']}")
                with c3:
                    st.write(f"**Telefone:** {ben['Fone 1'] if acesso_total else '🔒'}")
                    st.write(f"**CAR:** {ben['Código do CAR']}")

                # Detalhes das Unidades e Doações
                unds = df_und[df_und['Beneficiário'] == ben['Nome']]
                if f_bacia != "Todas":
                    unds = unds[unds['Unidade Hidro'] == f_bacia]

                for _, u in unds.iterrows():
                    st.markdown(f"---")
                    st.markdown(f"📍 **Unidade {u['ID und reabilitação']}** | {u['Unidade Hidro']} | {u['Tipo de Und']}")
                    
                    doas = df_doa[df_doa['ID Und Reab'] == u['ID und reabilitação']]
                    if not doas.empty:
                        st.dataframe(doas[['Data', 'SomaDequant', 'Política Pública', 'Origem das mudas']], hide_index=True, use_container_width=True)
                    if u['Observação']: st.caption(f"Nota: {u['Observação']}")

    else:
        # Dashboard Inicial
        st.info("Selecione um filtro ao lado para visualizar os dados.")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Beneficiários", len(df_ben))
        m2.metric("Total Unidades", len(df_und))
        m3.metric("Bacias Hidrográficas", len(bacia_list))
