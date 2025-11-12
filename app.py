import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# Configuração da página
st.set_page_config(page_title="Portal de Provas", page_icon="🎓")

# --- CONEXÃO MODERNA (CORRIGE O ERRO 200) ---
@st.cache_resource
def conectar_banco_dados():
    # Definimos o escopo de permissão
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # Lê as informações do cofre (Secrets)
        info_conta = dict(st.secrets["gcp_service_account"])
        
        # Cria as credenciais usando a biblioteca nova (google-auth)
        creds = Credentials.from_service_account_info(info_conta, scopes=scopes)
        
        # Autoriza o gspread
        client = gspread.authorize(creds)
        
        # Abre a planilha
        return client.open("Sistema de Provas Acadêmico")
        
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
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
        
        if st.form_submit_button("Salvar"):
            if not (curso and turma and nome_prova and gabarito):
                st.warning("Preencha todos os campos.")
            else:
                try:
                    aba = planilha.worksheet("Provas")
                    aba.append_row([curso, turma, turno, nome_prova, gabarito.replace(" ", "")])
                    st.success("Prova salva!")
                except:
                    st.error("A aba 'Provas' não existe na planilha.")

# ==================================================
# ÁREA DO ALUNO
# ==================================================
else:
    st.subheader("Realizar Prova")
    
    c1, c2, c3 = st.columns(3)
    f_curso = c1.text_input("Curso")
    f_turma = c2.text_input("Turma")
    f_turno = c3.selectbox("Turno", ["Manhã", "Tarde", "Noite"])
    
    if st.button("Buscar Provas"):
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
            st.error("Erro ao ler a planilha.")

    if 'provas' in st.session_state and st.session_state['provas']:
        lista_provas = st.session_state['provas']
        
        if not lista_provas:
            st.warning("Nenhuma prova encontrada para esses dados.")
        else:
            st.write("---")
            escolha = st.selectbox("Escolha a prova:", [p['nome_prova'] for p in lista_provas])
            prova = next(p for p in lista_provas if p['nome_prova'] == escolha)
            
            st.info(f"Prova: *{prova['nome_prova']}*")
            
            with st.form("resposta"):
                nome = st.text_input("Seu Nome")
                resp = st.text_input("Respostas (Ex: A,B,C)").upper()
                
                if st.form_submit_button("Entregar"):
                    if not nome or not resp:
                        st.error("Preencha tudo.")
                    else:
                        gab = prova['gabarito_oficial'].split(',')
                        alu = resp.replace(" ", "").split(',')
                        acertos = sum([1 for i in range(min(len(gab), len(alu))) if gab[i] == alu[i]])
                        total = len(gab)
                        nota = (acertos/total)*100
                        
                        if nota >= 70:
                            st.balloons()
                            st.success(f"Aprovado! Nota: {nota:.1f}%")
                        else:
                            st.error(f"Nota: {nota:.1f}%")
                            
                        planilha.worksheet("Submissoes").append_row([
                            nome, prova['curso'], prova['turma'], prova['turno'], 
                            prova['nome_prova'], resp, acertos, total
                        ])
