import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import os
from PIL import Image

# 1. Configuração da Página e Identidade Visual (Cores Seagri)
st.set_page_config(page_title="Seagri - Reflorestar", layout="wide", page_icon="🌳")

st.markdown("""
    <style>
    /* Fundo do Menu Lateral (Azul Seagri) */
    [data-testid="stSidebar"] {
        background-color: #0066b3;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    /* Títulos Principais */
    h1, h2 {
        color: #0066b3 !important;
    }
    /* Botões e Sucessos (Verde) */
    .stAlert {
        background-color: #e8f5e9;
        border: 1px solid #2e7d32;
    }
    /* Cards de Beneficiário (Borda Amarela/Laranja) */
    .stExpander {
        border: 2px solid #f39200 !important;
        border-radius: 10px !important;
        background-color: #ffffff;
    }
    /* Estilo das Métricas */
    [data-testid="stMetricValue"] {
        color: #f39200 !important;
    }
    /* Tabela Interna */
    .stDataFrame {
        border: 1px solid #2e7d32;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Funções de Suporte
def dms_to_decimal(coord_str):
    try:
        if not coord_str or pd.isna(coord_str): return None
        # Limpa e busca números de coordenadas
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
            for root, dirs, files in os.walk("."):
                if nome in files:
                    return pd.read_csv(os.path.join(root, nome)).fillna("")
            return pd.DataFrame()

        df_ben = ler_csv('cadastro_beneficiarios.csv')
        df_und = ler_csv('cadastro_unidades.csv')
        df_doa = ler_csv('cadastro_doacoes.csv')
        return df_ben, df_und, df_doa
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None, None, None

# 3. Cabeçalho Dinâmico (Busca o logo em qualquer pasta do repositório)
df_ben, df_und, df_doa = carregar_dados()

# Tenta encontrar o logo
logo_path = "logo_seagri.png"
for root, dirs, files in os.walk("."):
    if "logo_seagri.png" in files:
        logo_path = os.path.join(root, "logo_seagri.png")
        break

col_logo, col_tit = st.columns([1, 4])
with col_logo:
    if os.path.exists(logo_path):
        st.image(logo_path, width=160)
    else:
        st.info("💡 Suba o arquivo 'logo_seagri.png' no seu GitHub para exibir o logo aqui.")

with col_tit:
    st.title("Sistema Reflorestar - SEAGRI-DF")
    st.subheader("Painel de Controle e Consulta de Mudas")

# 4. Interface de Filtros
if df_ben is not None and not df_ben.empty:
    st.sidebar.markdown("### 🔍 Filtros de Consulta")
    busca_texto = st.sidebar.text_input("Busca por Nome, CPF, CNPJ ou CAR")
    
    localidades = sorted([l for l in df_ben['IDLocalidade'].unique() if l])
    localidade_sel = st.sidebar.selectbox("Filtrar por Localidade / R.A.", ["Todas"] + localidades)

    bacias = sorted([b for b in df_und['Unidade Hidro'].unique() if b])
    bacia_sel = st.sidebar.selectbox("Filtrar por Bacia Hidrográfica", ["Todas"] + bacias)

    # Lógica de Filtro combinada
    res_ben = df_ben.copy()
    if busca_texto:
        res_ben = res_ben[res_ben.apply(lambda r: r.astype(str).str.contains(busca_texto, case=False).any(), axis=1)]
    if localidade_sel != "Todas":
        res_ben = res_ben[res_ben['IDLocalidade'] == localidade_sel]

    # Exibição
    if busca_texto or localidade_sel != "Todas" or bacia_sel != "Todas":
        for _, ben in res_ben.iterrows():
            unds = df_und[df_und['Beneficiário'] == ben['Nome']]
            if bacia_sel != "Todas":
                unds = unds[unds['Unidade Hidro'] == bacia_sel]
                if unds.empty: continue

            with st.expander(f"👤 {ben['Nome'].upper()}", expanded=True):
                # Informações do Beneficiário em colunas limpas
                c1, c2, c3 = st.columns([1.5, 1.5, 1])
                with c1:
                    st.markdown(f"**CPF/CNPJ:** {ben['CPF'] or ben['CNPJ']}")
                    st.markdown(f"**Tamanho da Área:** {ben['Tamanho da propriedade (ha)']} ha")
                with c2:
                    st.markdown(f"**Processo SEI:** :green[{ben['N° Processo SEI']}]")
                    st.markdown(f"**Localidade:** {ben['IDLocalidade']}")
                with c3:
                    st.markdown(f"**CAR:** {ben['Código do CAR']}")
                    st.markdown(f"**Fone:** {ben['Fone 1']}")

                if ben['Observações']:
                    st.caption(f"ℹ️ **Obs:** {ben['Observações']}")

                # Unidades e Doações
                st.markdown("---")
                if not unds.empty:
                    m = folium.Map(location=[-15.75, -48.00], zoom_start=10)
                    tem_mapa = False

                    for _, u in unds.iterrows():
                        # Layout da Unidade
                        st.markdown(f"📍 **Unidade {u['ID und reabilitação']}** - *{u['Tipo de Und']}*")
                        
                        col_u1, col_u2 = st.columns([1, 2])
                        with col_u1:
                            st.write(f"**Bacia:** {u['Unidade Hidro']}")
                            if u['Observação']: st.write(f"**Obs Unidade:** {u['Observação']}")
                        
                        with col_u2:
                            doas = df_doa[df_doa['ID Und Reab'] == u['ID und reabilitação']]
                            if not doas.empty:
                                st.dataframe(doas[['Data', 'SomaDequant', 'Política Pública', 'Origem das mudas']], hide_index=True)
                            else:
                                st.write("Nenhuma doação registrada.")

                        # Coordenadas do Mapa
                        lat = dms_to_decimal(u['Coordenada Geográfica da Und de Reab']) or dms_to_decimal(ben['Coordenada Geo'])
                        if lat:
                            folium.Marker([lat, -48.0], popup=f"U-{u['ID und reabilitação']}").add_to(m)
                            tem_mapa = True
                    
                    if tem_mapa:
                        st_folium(m, width=1100, height=350, key=f"map_{ben['ID Beneficiário']}")
                else:
                    st.warning("Nenhuma unidade cadastrada para este beneficiário nesta bacia.")
    else:
        # Dashboard Inicial
        st.markdown("### 📊 Estatísticas Gerais")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Beneficiários", len(df_ben))
        total_mudas = pd.to_numeric(df_doa['SomaDequant'], errors='coerce').sum()
        col2.metric("Mudas Distribuídas", f"{int(total_mudas):,}")
        col3.metric("Bacias Hidrográficas", len(df_und['Unidade Hidro'].unique()))
        
        st.divider()
        st.success("Bem-vindo! Utilize os filtros da barra lateral para pesquisar.")

else:
    st.error("Verifique se os arquivos CSV foram subidos corretamente no GitHub.")
