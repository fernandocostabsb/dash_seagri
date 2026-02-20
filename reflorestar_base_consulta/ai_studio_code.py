import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import os

# Configuração da Página
st.set_page_config(page_title="Seagri - Dashboard de Mudas", layout="wide")

# Função para limpar e converter coordenadas
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

# Função para carregar os arquivos (ajustada para nuvem)
def carregar_dados():
    # Procura na pasta atual ou subpastas
    arquivos = {
        'ben': 'cadastro_beneficiarios.csv',
        'und': 'cadastro_unidades.csv',
        'doa': 'cadastro_doacoes.csv'
    }
    
    dfs = {}
    for chave, nome in arquivos.items():
        # Tenta achar o arquivo no diretório raiz ou dentro da sua pasta
        caminho_tentativa = None
        for root, dirs, files in os.walk("."):
            if nome in files:
                caminho_tentativa = os.path.join(root, nome)
                break
        
        if caminho_tentativa:
            dfs[chave] = pd.read_csv(caminho_tentativa).fillna("")
        else:
            st.error(f"Arquivo não encontrado: {nome}")
            return None, None, None
            
    return dfs['ben'], dfs['und'], dfs['doa']

try:
    df_ben, df_und, df_doa = carregar_dados()

    if df_ben is not None:
        st.title("🌳 Sistema de Consulta Seagri - Reflorestar")
        
        # BARRA LATERAL
        st.sidebar.header("🔍 Pesquisa")
        busca = st.sidebar.text_input("Digite Nome, CPF, CNPJ ou CAR:")

        if busca:
            # Filtra em todas as colunas do cadastro de beneficiários
            mask = df_ben.apply(lambda row: row.astype(str).str.contains(busca, case=False).any(), axis=1)
            resultados = df_ben[mask]

            if not resultados.empty:
                for _, ben in resultados.iterrows():
                    with st.expander(f"👤 Beneficiário: {ben['Nome']}", expanded=True):
                        c1, c2, c3 = st.columns(3)
                        c1.write(f"**ID:** {ben['ID Beneficiário']}")
                        c2.write(f"**CPF/CNPJ:** {ben['CPF'] or ben['CNPJ']}")
                        c3.write(f"**CAR:** {ben['Código do CAR']}")

                        # Unidades e Doações
                        unidades = df_und[df_und['Beneficiário'] == ben['Nome']]
                        if not unidades.empty:
                            m = folium.Map(location=[-15.7, -48.0], zoom_start=9)
                            tem_mapa = False
                            
                            for _, u in unidades.iterrows():
                                st.divider()
                                st.subheader(f"📍 Unidade {u['ID und reabilitação']}")
                                st.write(f"**Tipo:** {u['Tipo de Und']} | **Bacia:** {u['Unidade Hidro']}")
                                
                                # Tenta pegar coordenadas
                                lat = dms_to_decimal(u['Coordenada Geográfica da Und de Reab']) or dms_to_decimal(ben['Coordenada Geo'])
                                lon = -48.0 # Valor padrão caso não ache longitude exata no texto
                                
                                if lat:
                                    folium.Marker([lat, lon], popup=f"Unidade {u['ID und reabilitação']}").add_to(m)
                                    tem_mapa = True
                                
                                # Doações desta unidade
                                doacoes = df_doa[df_doa['ID Und Reab'] == u['ID und reabilitação']]
                                if not doacoes.empty:
                                    st.write("**📦 Histórico de Doações:**")
                                    st.dataframe(doacoes[['ID fornecimento', 'Data', 'SomaDequant', 'Política Pública']], hide_index=True)
                                else:
                                    st.info("Sem doações registradas para esta unidade.")
                            
                            if tem_mapa:
                                st_folium(m, width=700, height=300, key=f"map_{ben['ID Beneficiário']}")
                        else:
                            st.warning("Nenhuma unidade de plantio vinculada.")
            else:
                st.error("Nenhum registro encontrado.")
        else:
            # Dashboard Inicial
            st.info("Utilize a barra lateral para pesquisar um beneficiário.")
            col1, col2 = st.columns(2)
            col1.metric("Total Beneficiários", len(df_ben))
            qtd_total = pd.to_numeric(df_doa['SomaDequant'], errors='coerce').sum()
            col2.metric("Total de Mudas", f"{int(qtd_total):,}")

except Exception as e:
    st.error(f"Erro ao carregar sistema: {e}")
