import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Portal de Provas", page_icon="🎓")

# --- CONEXÃO NATIVA (PADRÃO TOML) ---
@st.cache_resource
def conectar_banco_dados():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # 1. Tenta ler os segredos. Se der erro aqui, mostra quais chaves existem para debug.
        if "gcp_service_account" not in st.secrets:
            st.error("ERRO: A chave 'gcp_service_account' não foi encontrada.")
            st.write("Chaves encontradas no sistema:", list(st.secrets.keys()))
            st.stop()

        # 2. Pega o dicionário direto do arquivo TOML
        info_conta = dict(st.secrets["gcp_service_account"])
        
        # 3. Garante que a chave privada tenha as quebras de linha corretas
        # O TOML às vezes remove os \n, então recolocamos por segurança
        if "private_key" in info_conta:
            info_conta["private_key"] = info_conta["private_key"].replace("\\n", "\n")
        
        # 4. Conecta
        creds = Credentials.from_service_account_info(info_conta, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("Sistema de Provas Acadêmico")
        
    except Exception as e:
        st.error(f"Erro Técnico: {e}")
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
                    st.success("Salvo com sucesso!")
                except:
                    st.error("A aba 'Provas' não existe.")

# ==================================================
# ÁREA DO ALUNO
# ==================================================
else:
    st.subheader("Realizar Prova")
    c1, c2, c3 = st.columns(3)
    f_curso = c1.text_input("Seu Curso")
    f_turma = c2.text_input("Sua Turma")
    f_turno = c3.selectbox("Seu Turno", ["Manhã", "Tarde", "Noite"])
    
    if st.button("🔍 Buscar"):
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
                st.warning("Nada encontrado.")
        except:
            st.error("Erro ao ler planilha.")

    if 'provas' in st.session_state and st.session_state['provas']:
        lista = st.session_state['provas']
        if not lista:
            st.warning("Sem resultados.")
        else:
            st.write("---")
            escolha = st.selectbox("Prova:", [p['nome_prova'] for p in lista])
            prova = next(p for p in lista if p['nome_prova'] == escolha)
            
            st.info(f"Fazendo: *{prova['nome_prova']}*")
            with st.form("resp"):
                nome = st.text_input("Nome")
                resp = st.text_input("Respostas (Ex: A,B,C)").upper()
                
                if st.form_submit_button("Enviar"):
                    if nome and resp:
                        gab = prova['gabarito_oficial'].split(',')
                        alu = resp.replace(" ", "").split(',')
                        acertos = sum([1 for i in range(min(len(gab), len(alu))) if gab[i] == alu[i]])
                        total = len(gab)
                        nota = (acertos/total)*100
                        
                        if nota >= 70: st.success(f"Nota: {nota:.1f}%")
                        else: st.error(f"Nota: {nota:.1f}%")
                        
                        planilha.worksheet("Submissoes").append_row([
                            nome, prova['curso'], prova['turma'], prova['turno'], 
                            prova['nome_prova'], resp, acertos, total
                        ])
