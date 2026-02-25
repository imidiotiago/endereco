import streamlit as st
import requests
import pandas as pd
import re
import io

# --- FUNÇÕES DE UTILIDADE ---
def clean_text(text):
    if isinstance(text, str):
        return re.sub(r'[^ -~]', '', text)
    return text

def gera_token_wms(client_id, client_secret):
    url = "https://supply.rac.totvs.app/totvs.rac/connect/token"
    data = {
        "client_id": client_id, 
        "client_secret": client_secret,
        "grant_type": "client_credentials", 
        "scope": "authorization_api"
    }
    try:
        res = requests.post(url, data=data, timeout=15)
        return res.json().get("access_token") if res.status_code == 200 else None
    except:
        return None

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="WMS Address Query", layout="wide")
st.title("📍 Consulta de Endereços e Depósitos WMS")

with st.sidebar:
    st.header("🔑 Credenciais WMS")
    c_id = st.text_input("Client ID", type="password", key="addr_cid")
    c_secret = st.text_input("Client Secret", type="password", key="addr_sec")
    
    st.divider()
    
    st.header("📍 Localização")
    u_id = st.text_input("Unidade ID (UUID)", placeholder="Ex: ac275b55-90f8-44b8-b8cb-bdcfca969526", key="addr_uid")
    
    st.caption("🔒 Dados protegidos por sessão.")

# --- BOTÃO DE EXECUÇÃO ---
if st.button("🚀 Consultar Endereços"):
    if not all([c_id, c_secret, u_id]):
        st.error("⚠️ Por favor, preencha todos os campos na barra lateral.")
    else:
        token = gera_token_wms(c_id, c_secret)
        
        if not token:
            st.error("❌ Falha na autenticação. Verifique o Client ID e Secret.")
        else:
            all_data = []
            page = 1
            progress_text = st.empty()
            
            API_URL = "https://supply.logistica.totvs.app/wms/query/api/v1/enderecos"

            with st.spinner("Mapeando endereços..."):
                while True:
                    params = {
                        "page": page, 
                        "pageSize": 500, 
                        "unidadeId": u_id.strip()
                    }
                    
                    try:
                        headers = {"Authorization": f"Bearer {token}"}
                        res = requests.get(API_URL, params=params, headers=headers, timeout=60)
                        
                        if res.status_code == 200:
                            data = res.json()
                            items = data.get('items', [])
                            
                            if not items:
                                break
                            
                            for endereco in items:
                                dados_deposito = endereco.get('deposito', {}) or {}
                                
                                all_data.append({
                                    'ID Endereço': clean_text(endereco.get('id')),
                                    'Descrição Endereço': clean_text(endereco.get('descricao')),
                                    'Código de Barras': clean_text(endereco.get('codigoBarras')),
                                    'Depósito': clean_text(dados_deposito.get('descricao')),
                                    'ID Depósito': clean_text(dados_deposito.get('id')),
                                    'Situação': clean_text(endereco.get('situacao'))
                                })
                            
                            progress_text.info(f"⏳ Lendo página {page}... {len(all_data)} endereços mapeados.")
                            
                            if not data.get('hasNext'):
                                break
                            page += 1
                        else:
                            st.error(f"Erro na API (Página {page}): Status {res.status_code}")
                            break
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")
                        break

            if all_data:
                progress_text.empty()
                df = pd.DataFrame(all_data)
                
                st.success(f"✅ Sucesso! {len(all_data)} endereços carregados.")
                
                # Exibição da Tabela
                st.dataframe(df, use_container_width=True)
                
                # Preparação do Excel
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Enderecos_WMS')
                
                st.download_button(
                    label="📥 Baixar Lista de Endereços",
                    data=buf.getvalue(),
                    file_name=f"enderecos_wms_{u_id[:8]}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("⚠️ Nenhum endereço encontrado para esta Unidade ID.")
