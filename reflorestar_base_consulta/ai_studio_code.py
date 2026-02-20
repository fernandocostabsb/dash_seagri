import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import os
from PIL import Image

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Seagri - Reflorestar", layout="wide", page_icon="🌳")

# 2. ESTILIZAÇÃO PARA ACESSIBILIDADE (CLARO/ESCURO) E CORES SEAGRI
st.markdown("""
    <style>
    /* Estilização da Sidebar */
    [data-testid="stSidebar"] { background-color: #0066b3; }
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* Input de texto na sidebar - garantir visibilidade */
    .stTextInput input { color: black !important; background-color: white !important; }

    /* Cores de títulos e textos principais */
    h1, h2, h3 { color: #0066b3 !important; }
    
    /* Card de Resultado (Fundo fixo para leitura universal) */
    .result-card {
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #f39200;
        margin-bottom: 20px;
        color: #1a1a1a !important; /* Fonte escura para leitura em qualquer tema */
    }
    
    .stExpander { border: 1px solid #0066b3 !important; background-color: #f0f2f6; }
    
    /* Estilo para dados ocultos */
    .hidden-data { color: #d32f2f; font-style: italic; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 3. FUNÇÕES DE SUPORTE E CARREGAMENTO
def dms_to_decimal(coord_str):
    try:
        if not coord_str or pd.isna(coord_str): return None
        parts = re.findall(r"(\d+)°(\d+)'?([\d.]+)?", str(coord_str))
        if not parts: return None
        d, m, s = float(parts[0][0]), float(parts[0][1]), float(parts[0][2] if parts[0][2] else 0)
        dec = d + m/60 + s/3600
        if any(c in str(coord_str).upper() for c in ['S', 'W', 'O']): dec *= -1
        return dec
    except: return None

@st.cache_data
def carregar_dados():
    def ler_csv(nome):
        for root, dirs, files in os.walk("."):
            if nome in files:
                return pd.read_csv(os.path.join(root, nome), dtype=str).fillna("")
        return pd.DataFrame()
    return ler_csv('cadastro_beneficiarios.csv'), ler_csv('cadastro_unidades.csv'), ler_csv('cadastro_doacoes.csv'), ler_csv('cadastro_seagri_interno.csv')

df_ben, df_und, df_doa, df_interno = carregar_dados()

# 4. SISTEMA DE AUTORIZAÇÃO (LOGIN) NA SIDEBAR
st.sidebar.markdown("## 🔐 Acesso Restrito")
with st.sidebar.expander("Identificação do Usuário"):
    user_email = st.text_input("E-mail corporativo")
    user_fone = st.text_input("Telefone (apenas números)")
    
    # Validação do Usuário
    acesso_total = False
    if user_email and user_fone:
        # Limpa telefone para busca
        fone_busca = re.sub(r'\D', '', user_fone)
        match = df_interno[
            (df_interno['Email'].str.lower() == user_email.lower()) & 
            (df_interno['Fone'].str.replace(r'\D', '', regex=True).str.contains(fone_busca))
        ]
        if not match.empty:
            st.success("✅ Acesso Total Autorizado")
            acesso_total = True
        else:
            st.error("❌ Usuário não cadastrado.")

# 5. CABEÇALHO COM LOGO
logo_path = "logo_seagri.png"
for root, dirs, files in os.walk("."):
    if "logo_seagri.png" in files:
        logo_path = os.path.join(root, "logo_seagri.png")
        break

col_logo, col_tit = st.columns([1, 4])
with col_logo:
    if os.path.exists(logo_path): st.image(logo_path, width=140)
with col_tit:
    st.title("Sistema Reflorestar - SEAGRI-DF")
    st.write(f"Nível de Acesso: {'**TOTAL (INTERNO)**' if acesso_total else '**RESTRITO (PÚBLICO)**'}")

# 6. FILTROS DE CONSULTA
if df_ben is not None and not df_ben.empty:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔎 Critérios de Busca")
    busca_texto = st.sidebar.text_input("Busca Nome, CPF, CAR ou Telefone")
    
    localidades = sorted([l for l in df_ben['IDLocalidade'].unique() if l])
    localidade_sel = st.sidebar.selectbox("Filtrar por Localidade / R.A.", ["Todas"] + localidades)

    bacias = sorted([b for b in df_und['Unidade Hidro'].unique() if b])
    bacia_sel = st.sidebar.selectbox("Filtrar por Bacia Hidrográfica", ["Todas"] + bacias)

    # Lógica de Filtragem
    res_ben = df_ben.copy()
    if busca_texto:
        busca_num = re.sub(r'\D', '', busca_texto)
        res_ben = res_ben[
            res_ben['Nome'].str.contains(busca_texto, case=False) |
            res_ben['Código do CAR'].str.contains(busca_texto, case=False) |
            res_ben['CPF'].str.replace(r'\D', '', regex=True).str.contains(busca_num) |
            res_ben['Fone 1'].str.replace(r'\D', '', regex=True).str.contains(busca_num)
        ]
    if localidade_sel != "Todas":
        res_ben = res_ben[res_ben['IDLocalidade'] == localidade_sel]

    # 7. EXIBIÇÃO DOS RESULTADOS
    if busca_texto or localidade_sel != "Todas" or bacia_sel != "Todas":
        for _, ben in res_ben.iterrows():
            unds = df_und[df_und['Beneficiário'] == ben['Nome']]
            if bacia_sel != "Todas":
                unds = unds[unds['Unidade Hidro'] == bacia_sel]
                if unds.empty: continue

            # Títulos sempre visíveis
            with st.expander(f"👤 {ben['Nome'].upper()}", expanded=True):
                # Formatação dos dados sensíveis
                cpf_display = ben['CPF'] if acesso_total else "🔒 ACESSO RESTRITO"
                fone_display = ben['Fone 1'] if acesso_total else "🔒 ACESSO RESTRITO"
                
                # Layout de colunas para o Beneficiário
                c1, c2, c3 = st.columns([1.5, 1.5, 1])
                with c1:
                    st.write(f"**CPF/CNPJ:** {cpf_display}")
                    st.write(f"**Tamanho da Área:** {ben['Tamanho da propriedade (ha)']} ha")
                with c2:
                    st.write(f"**Processo SEI:** :green[{ben['N° Processo SEI']}]")
                    st.write(f"**Localidade:** {ben['IDLocalidade']}")
                with c3:
                    st.write(f"**Telefone:** {fone_display}")
                    st.write(f"**CAR:** {ben['Código do CAR']}")

                if ben['Observações']:
                    st.warning(f"**Obs Beneficiário:** {ben['Observações']}")

                # Seção de Unidades
                st.markdown("---")
                if not unds.empty:
                    m = folium.Map(location=[-15.7, -48.0], zoom_start=10)
                    tem_mapa = False

                    for _, u in unds.iterrows():
                        st.markdown(f"📍 **Unidade {u['ID und reabilitação']}** - *{u['Tipo de Und']}*")
                        cu1, cu2 = st.columns([1, 2])
                        with cu1:
                            st.write(f"**Bacia:** {u['Unidade Hidro']}")
                            if u['Observação']: st.info(f"**Obs Unidade:** {u['Observação']}")
                        
                        with cu2:
                            doas = df_doa[df_doa['ID Und Reab'] == u['ID und reabilitação']]
                            if not doas.empty:
                                st.dataframe(doas[['Data', 'ID fornecimento', 'SomaDequant', 'Política Pública', 'Origem das mudas']], hide_index=True)
                            else:
                                st.write("Nenhuma doação registrada.")

                        # Coordenadas
                        lat = dms_to_decimal(u['Coordenada Geográfica da Und de Reab']) or dms_to_decimal(ben['Coordenada Geo'])
                        if lat:
                            folium.Marker([lat, -48.0], popup=f"Unidade {u['ID und reabilitação']}").add_to(m)
                            tem_mapa = True
                    
                    if tem_mapa:
                        st_folium(m, width=1000, height=350, key=f"map_{ben['ID Beneficiário']}")
    else:
        # Dashboard Resumo
        st.markdown("### 📊 Estatísticas Gerais")
        col1, col2, col3 = st.columns(3)
        col1.metric("Beneficiários Cadastrados", len(df_ben))
        total_mudas = pd.to_numeric(df_doa['SomaDequant'], errors='coerce').sum()
        col2.metric("Mudas Distribuídas (Acumulado)", f"{int(total_mudas):,}")
        col3.metric("Bacias Atendidas", len(df_und['Unidade Hidro'].unique()))
        
        st.info("Para visualizar dados sensíveis (CPF e Telefone), realize o login na barra lateral.")
else:
    st.error("Base de dados não encontrada.")
