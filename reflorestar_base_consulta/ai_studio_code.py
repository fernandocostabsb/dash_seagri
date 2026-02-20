import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import os
from PIL import Image

# 1. Configuração da Página
st.set_page_config(page_title="Seagri - Consulta Reflorestar", layout="wide", page_icon="🌳")

# CSS Estilizado Seagri
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #0066b3; }
    [data-testid="stSidebar"] * { color: white !important; }
    h1, h2, h3 { color: #0066b3 !important; }
    .stExpander { border: 2px solid #f39200 !important; border-radius: 10px !important; background-color: #fdfdfd; }
    [data-testid="stMetricValue"] { color: #2e7d32 !important; }
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
            for root, dirs, files in os.walk("."):
                if nome in files:
                    return pd.read_csv(os.path.join(root, nome)).fillna("")
            return pd.DataFrame()
        return ler_csv('cadastro_beneficiarios.csv'), ler_csv('cadastro_unidades.csv'), ler_csv('cadastro_doacoes.csv')
    except Exception as e:
        st.error(f"Erro nos arquivos: {e}")
        return None, None, None

df_ben, df_und, df_doa = carregar_dados()

# 3. Cabeçalho com Logo
logo_path = "logo_seagri.png"
for root, dirs, files in os.walk("."):
    if "logo_seagri.png" in files:
        logo_path = os.path.join(root, "logo_seagri.png")
        break

col_l, col_t = st.columns([1, 4])
with col_l:
    if os.path.exists(logo_path): st.image(logo_path, width=150)
with col_t:
    st.title("Sistema Reflorestar - SEAGRI-DF")
    st.subheader("Consulta Consolidada: Beneficiários, Unidades e Doações")

# 4. Filtros e Busca
if df_ben is not None and not df_ben.empty:
    st.sidebar.markdown("### 🔍 Pesquisar Beneficiário")
    
    # Campo de busca principal (Nome, CPF, CAR ou TELEFONE)
    busca_texto = st.sidebar.text_input("Nome, CPF, CAR ou Telefone")
    
    localidades = sorted([l for l in df_ben['IDLocalidade'].unique() if l])
    localidade_sel = st.sidebar.selectbox("Localidade / R.A.", ["Todas"] + localidades)

    bacias = sorted([b for b in df_und['Unidade Hidro'].unique() if b])
    bacia_sel = st.sidebar.selectbox("Bacia Hidrográfica", ["Todas"] + bacias)

    # --- Lógica de busca avançada (incluindo limpeza de telefone) ---
    res_ben = df_ben.copy()
    if busca_texto:
        # Limpa o texto de busca para focar em números caso seja CPF ou Telefone
        busca_limpa = re.sub(r'\D', '', busca_texto)
        
        # Filtra se o texto está no Nome ou CAR, OU se os números estão no CPF/CNPJ/Telefone
        res_ben = res_ben[
            res_ben['Nome'].str.contains(busca_texto, case=False) |
            res_ben['Código do CAR'].str.contains(busca_texto, case=False) |
            res_ben['CPF'].str.replace(r'\D', '', regex=True).str.contains(busca_limpa) |
            res_ben['Fone 1'].str.replace(r'\D', '', regex=True).str.contains(busca_limpa) |
            res_ben['Fone 2'].str.replace(r'\D', '', regex=True).str.contains(busca_limpa)
        ]

    if localidade_sel != "Todas":
        res_ben = res_ben[res_ben['IDLocalidade'] == localidade_sel]

    # 5. Apresentação dos Resultados
    if busca_texto or localidade_sel != "Todas" or bacia_sel != "Todas":
        for _, ben in res_ben.iterrows():
            unds = df_und[df_und['Beneficiário'] == ben['Nome']]
            if bacia_sel != "Todas":
                unds = unds[unds['Unidade Hidro'] == bacia_sel]
                if unds.empty: continue

            with st.expander(f"👤 {ben['Nome'].upper()}", expanded=True):
                # Informações principais conforme solicitado
                c1, c2, c3 = st.columns([1.5, 1.5, 1.2])
                with c1:
                    st.write(f"**CPF/CNPJ:** {ben['CPF'] or ben['CNPJ']}")
                    st.write(f"**Telefones:** {ben['Fone 1']} / {ben['Fone 2']}")
                    st.write(f"**Tamanho Propriedade:** {ben['Tamanho da propriedade (ha)']} ha")
                with c2:
                    st.write(f"**Processo SEI:** :green[{ben['N° Processo SEI']}]")
                    st.write(f"**Localidade/RA:** {ben['IDLocalidade']}")
                with c3:
                    st.write(f"**Código CAR:** {ben['Código do CAR']}")
                    if ben['Observações']:
                        st.warning(f"**Obs:** {ben['Observações']}")

                # Unidades e Histórico
                st.markdown("---")
                if not unds.empty:
                    m = folium.Map(location=[-15.75, -48.00], zoom_start=10)
                    tem_mapa = False

                    for _, u in unds.iterrows():
                        st.markdown(f"📍 **Unidade {u['ID und reabilitação']}** - *{u['Tipo de Und']}*")
                        
                        cu1, cu2 = st.columns([1, 2])
                        with cu1:
                            st.write(f"**Bacia:** {u['Unidade Hidro']}")
                            if u['Observação']: st.info(f"**Obs Unidade:** {u['Observação']}")
                        
                        with cu2:
                            # Busca doações desta unidade
                            doas = df_doa[df_doa['ID Und Reab'] == u['ID und reabilitação']]
                            if not doas.empty:
                                # Retorna Origem, ID Fornecimento e Política conforme solicitado
                                st.dataframe(doas[['Data', 'ID fornecimento', 'SomaDequant', 'Política Pública', 'Origem das mudas']], hide_index=True)
                            else:
                                st.write("*(Sem doações registradas)*")

                        # Mapa
                        lat = dms_to_decimal(u['Coordenada Geográfica da Und de Reab']) or dms_to_decimal(ben['Coordenada Geo'])
                        if lat:
                            folium.Marker([lat, -48.0], popup=f"U-{u['ID und reabilitação']}").add_to(m)
                            tem_mapa = True
                    
                    if tem_mapa:
                        st_folium(m, width=1000, height=300, key=f"map_{ben['ID Beneficiário']}")
    else:
        # Dashboard Inicial Resumido
        st.markdown("### 📊 Estatísticas Gerais do Programa")
        c1, c2, c3 = st.columns(3)
        c1.metric("Beneficiários na Base", len(df_ben))
        total_mudas = pd.to_numeric(df_doa['SomaDequant'], errors='coerce').sum()
        c2.metric("Mudas Distribuídas", f"{int(total_mudas):,}")
        c3.metric("Bacias Hidrográficas", len(df_und['Unidade Hidro'].unique()))
        st.info("Utilize a barra lateral para realizar sua consulta.")
