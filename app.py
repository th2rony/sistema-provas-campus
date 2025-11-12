import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# Configuração da página
st.set_page_config(page_title="Portal de Provas", page_icon="🎓")

# --- CONEXÃO BLINDADA (MÉTODO JSON PURO) ---
@st.cache_resource
def conectar_banco_dados():
    # Definimos o escopo de permissão
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # 1. Lê o JSON inteiro como um texto único dos Secrets
        json_bruto = st.secrets["google_credentials_json"]
        
        # 2. O Python converte o texto em um dicionário (objeto) real
        # Isso resolve 100% dos problemas de quebra de linha (\n)
        info_conta = json.loads(json_bruto)
        
        # 3. Cria as credenciais
        creds = Credentials.from_service_account_info(info_conta, scopes=scopes)
        
        # 4. Autoriza e conecta
        client = gspread.authorize(creds)
        return client.open("Sistema de Provas Acadêmico")
        
    except Exception as e:
        st.error(f"Erro Crítico na Conexão: {e}")
        st.stop()

# Conecta ao banco de dados
planilha = conectar_banco_dados()

# --- TELA PRINCIPAL ---
st.title("🎓 Portal Acadêmico")
perfil = st.radio("Acesso:", ["Professor", "Aluno"], horizontal=True)
st.divider()

# ==================================================
# ÁREA DO PROFESSOR
# ==================================================
if perfil == "Professor":
    st.subheader("Cadastrar Prova")
    
    with st.form("form_prof"):
        c1, c2 = st.columns(2)
        curso = c1.text_input("Curso")
        turma = c2.text_input("Turma")
        turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite"])
        nome_prova = st.text_input("Nome da Prova")
        gabarito = st.text_input("Gabarito (Ex: A,B,C)").upper()
        
        if st.form_submit_button("Salvar Prova"):
            if not (curso and turma and nome_prova and gabarito):
                st.warning("Preencha todos os campos.")
            else:
                try:
                    aba = planilha.worksheet("Provas")
                    aba.append_row([curso, turma, turno, nome_prova, gabarito.replace(" ", "")])
                    st.success("Prova salva com sucesso!")
                except:
                    st.error("Erro: A aba 'Provas' não existe na planilha.")

# ==================================================
# ÁREA DO ALUNO
# ==================================================
else:
    st.subheader("Realizar Prova")
    
    c1, c2, c3 = st.columns(3)
    f_curso = c1.text_input("Seu Curso")
    f_turma = c2.text_input("Sua Turma")
    f_turno = c3.selectbox("Seu Turno", ["Manhã", "Tarde", "Noite"])
    
    if st.button("🔍 Buscar Provas"):
        try:
            aba = planilha.worksheet("Provas")
            dados = aba.get_all_records()
            df = pd.DataFrame(dados)
            
            if not df.empty:
                df = df.astype(str)
                filtro = (
                    (df['curso'].str.lower() == f_curso.lower()) &
                    (df['turma'].str.lower() == f_turma.lower()) &
                    (df['turno'].str.lower() == f_turno.lower())
                )
                st.session_state['provas'] = df[filtro].to_dict('records')
            else:
                st.warning("Nenhuma prova encontrada.")
        except:
            st.error("Erro ao ler planilha. Verifique se tem dados na aba 'Provas'.")

    if 'provas' in st.session_state and st.session_state['provas']:
        lista_provas = st.session_state['provas']
        
        if not lista_provas:
            st.warning("Nenhuma prova encontrada.")
        else:
            st.write("---")
            escolha = st.selectbox("Selecione a prova:", [p['nome_prova'] for p in lista_provas])
            prova = next(p for p in lista_provas if p['nome_prova'] == escolha)
            
            st.info(f"Realizando: *{prova['nome_prova']}*")
            
            with st.form("resposta"):
                nome = st.text_input("Seu Nome Completo")
                resp = st.text_input("Suas Respostas (Ex: A,B,C,D)").upper()
                
                if st.form_submit_button("✉️ Entregar Prova"):
                    if not nome or not resp:
                        st.error("Preencha seu nome e respostas.")
                    else:
                        gab = prova['gabarito_oficial'].split(',')
                        alu = resp.replace(" ", "").split(',')
                        acertos = sum([1 for i in range(min(len(gab), len(alu))) if gab[i] == alu[i]])
                        total = len(gab)
                        nota = (acertos/total)*100
                        
                        if nota >= 70:
                            st.balloons()
                            st.success(f"Nota: {nota:.1f}% ({acertos}/{total})")
                        else:
                            st.error(f"Nota: {nota:.1f}% ({acertos}/{total})")
                        
                        planilha.worksheet("Submissoes").append_row([
                            nome, prova['curso'], prova['turma'], prova['turno'], 
                            prova['nome_prova'], resp, acertos, total
                        ])
