import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import os
from PIL import Image

# 1. Configuração da Página e Identidade Visual
st.set_page_config(page_title="Seagri - Reflorestar", layout="wide", page_icon="🌳")

# CSS para aplicar as cores do logo (Azul, Amarelo, Laranja + Verde)
st.markdown("""
    <style>
    /* Cor de fundo do Menu Lateral (Azul Seagri) */
    [data-testid="stSidebar"] {
        background-color: #0066b3;
        color: white;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    /* Títulos e Subtítulos */
    h1, h2, h3 {
        color: #0066b3;
    }
    /* Botões e Filtros (Verde) */
    .stButton>button {
        background-color: #2e7d32;
        color: white;
        border-radius: 5px;
    }
    /* Estilo dos Cards de Beneficiário */
    .stExpander {
        border: 1px solid #ffcc00;
        border-radius: 10px;
    }
    /* Métricas (Laranja/Amarelo) */
    [data-testid="stMetricValue"] {
        color: #f39200;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Funções de Suporte
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
    try:
        def ler_csv(nome):
            caminho_final = nome
            for root, dirs, files in os.walk("."):
                if nome in files:
                    caminho_final = os.path.join(root, nome)
                    break
            return pd.read_csv(caminho_final).fillna("")

        df_ben = ler_csv('cadastro_beneficiarios.csv')
        df_und = ler_csv('cadastro_unidades.csv')
        df_doa = ler_csv('cadastro_doacoes.csv')
        return df_ben, df_und, df_doa
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None, None, None

# 3. Cabeçalho com Logo
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo_seagri.png"):
        img = Image.open("logo_seagri.png")
        st.image(img, width=150)
    else:
        st.warning("Suba o logo_seagri.png")

with col_titulo:
    st.title("Sistema Reflorestar - SEAGRI-DF")
    st.subheader("Consulta de Fornecimento de Mudas Nativas")

# 4. Processamento de Dados
df_ben, df_und, df_doa = carregar_dados()

if df_ben is not None:
    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.markdown("### 🔍 Painel de Busca")
    busca_texto = st.sidebar.text_input("Nome, CPF, CNPJ ou CAR")
    
    localidades = sorted(df_ben['IDLocalidade'].unique().tolist())
    localidade_sel = st.sidebar.selectbox("Localidade / R.A.", ["Todas"] + [l for l in localidades if l])

    bacias = sorted(df_und['Unidade Hidro'].unique().tolist())
    bacia_sel = st.sidebar.selectbox("Bacia / Unidade Hidro", ["Todas"] + [b for b in bacias if b])

    # Lógica de Filtro
    res_ben = df_ben.copy()
    if busca_texto:
        res_ben = res_ben[res_ben.apply(lambda r: r.astype(str).str.contains(busca_texto, case=False).any(), axis=1)]
    if localidade_sel != "Todas":
        res_ben = res_ben[res_ben['IDLocalidade'] == localidade_sel]

    # --- ÁREA PRINCIPAL ---
    if busca_texto or localidade_sel != "Todas" or bacia_sel != "Todas":
        for _, ben in res_ben.iterrows():
            # Filtro por bacia (está em outra tabela)
            unds = df_und[df_und['Beneficiário'] == ben['Nome']]
            if bacia_sel != "Todas":
                unds = unds[unds['Unidade Hidro'] == bacia_sel]
                if unds.empty: continue

            # Card do Beneficiário
            with st.expander(f"👤 {ben['Nome'].upper()}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.write(f"**CPF/CNPJ:** {ben['CPF'] or ben['CNPJ']}")
                c1.write(f"**Área Propriedade:** {ben['Tamanho da propriedade (ha)']} ha")
                
                c2.write(f"**Processo SEI:** :green[{ben['N° Processo SEI']}]")
                c2.write(f"**Localidade:** {ben['IDLocalidade']}")
                
                c3.write(f"**CAR:** {ben['Código do CAR']}")
                c3.write(f"**Telefone:** {ben['Fone 1']}")

                if ben['Observações']:
                    st.info(f"💡 **Observação Beneficiário:** {ben['Observações']}")

                # Unidades de Reabilitação
                st.markdown("---")
                st.markdown("#### 📍 Unidades de Reabilitação e Doações")
                
                if not unds.empty:
                    m = folium.Map(location=[-15.7, -48.0], zoom_start=10)
                    tem_mapa = False

                    for _, u in unds.iterrows():
                        col_und, col_tab = st.columns([1, 2])
                        with col_und:
                            st.success(f"**Unidade {u['ID und reabilitação']}**")
                            st.write(f"**Tipo:** {u['Tipo de Und']}")
                            st.write(f"**Bacia:** {u['Unidade Hidro']}")
                            if u['Observação']:
                                st.caption(f"*Obs Unidade: {u['Observação']}*")
                        
                        with col_tab:
                            doas = df_doa[df_doa['ID Und Reab'] == u['ID und reabilitação']]
                            if not doas.empty:
                                st.dataframe(doas[['ID fornecimento', 'Data', 'SomaDequant', 'Política Pública', 'Origem das mudas']], hide_index=True)
                            else:
                                st.write("Nenhuma doação para esta unidade.")

                        # Coordenadas
                        lat = dms_to_decimal(u['Coordenada Geográfica da Und de Reab']) or dms_to_decimal(ben['Coordenada Geo'])
                        if lat:
                            folium.Marker([lat, -48.0], popup=f"Unidade {u['ID und reabilitação']}").add_to(m)
                            tem_mapa = True
                    
                    if tem_mapa:
                        st_folium(m, width=1000, height=300, key=f"map_{ben['ID Beneficiário']}")
                else:
                    st.warning("Nenhuma unidade encontrada para os filtros de bacia selecionados.")

    else:
        # Dashboard Inicial (Resumo Geral) em Verde e Azul
        st.markdown("### 📊 Panorama Geral")
        col1, col2, col3 = st.columns(3)
        col1.metric("Beneficiários Atendidos", len(df_ben))
        
        mudas = pd.to_numeric(df_doa['SomaDequant'], errors='coerce').sum()
        col2.metric("Mudas Distribuídas", f"{int(mudas):,}")
        
        col3.metric("Bacias Hidrográficas", len(df_und['Unidade Hidro'].unique()))
        
        st.info("Utilize os filtros à esquerda para iniciar uma consulta detalhada.")

else:
    st.error("Erro ao carregar a base de dados. Verifique os arquivos CSV no GitHub.")
