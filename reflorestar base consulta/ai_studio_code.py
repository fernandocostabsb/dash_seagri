import pandas as pd
import io

def carregar_dados():
    # Carregando os arquivos (ajuste os nomes se necessário)
    # Nota: Usei sep=',' mas se for ponto-e-vírgula, mude para sep=';'
    try:
        df_beneficiarios = pd.read_csv('cadastro_beneficiarios.csv', low_memory=False)
        df_unidades = pd.read_csv('cadastro_unidades.csv', low_memory=False)
        df_doacoes = pd.read_csv('cadastro_doacoes.csv', low_memory=False)
        
        # Limpeza básica: remover espaços em branco dos nomes das colunas
        df_beneficiarios.columns = df_beneficiarios.columns.str.strip()
        df_unidades.columns = df_unidades.columns.str.strip()
        df_doacoes.columns = df_doacoes.columns.str.strip()
        
        return df_beneficiarios, df_unidades, df_doacoes
    except Exception as e:
        print(f"Erro ao carregar arquivos: {e}")
        return None, None, None

def consultar(termo_busca):
    df_ben, df_und, df_doa = carregar_dados()
    if df_ben is None: return

    # Normalizar termo de busca para string e remover pontuação de CPF/CNPJ/Fone
    termo = str(termo_busca).strip().lower()

    # Filtro no Cadastro de Beneficiários
    # Busca em múltiplas colunas
    resultado_ben = df_ben[
        df_ben['Nome'].str.contains(termo, case=False, na=False) |
        df_ben['CPF'].str.replace('[^0-9]', '', regex=True).str.contains(termo, na=False) |
        df_ben['CNPJ'].str.replace('[^0-9]', '', regex=True).str.contains(termo, na=False) |
        df_ben['Fone 1'].str.replace('[^0-9]', '', regex=True).str.contains(termo, na=False) |
        df_ben['Código do CAR'].str.contains(termo, case=False, na=False)
    ]

    if resultado_ben.empty:
        print("\nNenhum beneficiário encontrado.")
        return

    for _, ben in resultado_ben.iterrows():
        nome_ben = ben['Nome']
        id_ben = ben['ID Beneficiário']
        coord_ben = ben['Coordenada Geo']
        
        print("-" * 50)
        print(f"BENEFICIÁRIO: {nome_ben} (ID: {id_ben})")
        print(f"CPF/CNPJ: {ben['CPF'] if pd.notna(ben['CPF']) else ben['CNPJ']}")
        print(f"CAR: {ben['Código do CAR']}")
        print("-" * 50)

        # 1. Buscar Unidades de Reabilitação deste beneficiário
        # O cadastro de unidades liga pelo nome do beneficiário
        unidades_ben = df_und[df_und['Beneficiário'] == nome_ben]

        if unidades_ben.empty:
            print("Nenhuma unidade de reabilitação cadastrada.")
        else:
            print("\n>>> UNIDADES DE REABILITAÇÃO E LOCALIZAÇÃO:")
            for _, und in unidades_ben.iterrows():
                id_und = und['ID und reabilitação']
                tipo_und = und['Tipo de Und']
                # Localização: Prioriza a da Unidade, se não tiver, usa a do Beneficiário
                coord_und = und['Coordenada Geográfica da Und de Reab']
                loc_final = coord_und if pd.notna(coord_und) and str(coord_und).strip() != "" else coord_ben
                
                print(f"- ID Unidade: {id_und} | Tipo: {tipo_und}")
                print(f"  Localização (Coord): {loc_final}")

                # 2. Buscar Doações para esta unidade
                doacoes_und = df_doa[df_doa['ID Und Reab'] == id_und].copy()
                
                if not doacoes_und.empty:
                    # Extrair o ano da data (formato DD-MMM-AA)
                    doacoes_und['Ano'] = doacoes_und['Data'].str.extract(r'(\d{2})$')
                    doacoes_und['Ano'] = "20" + doacoes_und['Ano']
                    
                    print(f"  HISTÓRICO DE DOAÇÕES NESTA UNIDADE:")
                    for _, doa in doacoes_und.iterrows():
                        print(f"    * Fornecimento ID: {doa['ID fornecimento']} | Ano: {doa['Ano']} | Qtd: {doa['SomaDequant']} | Política: {doa['Política Pública']}")
                else:
                    print("    (Sem doações registradas para esta unidade)")
        print("\n")

# --- Interface Simples ---
if __name__ == "__main__":
    print("Ferramenta de Consulta Seagri - Mudas Nativas")
    while True:
        busca = input("Digite Nome, CPF, CNPJ, Telefone ou CAR (ou 'sair'): ")
        if busca.lower() == 'sair': break
        consultar(busca)