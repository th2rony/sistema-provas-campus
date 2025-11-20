import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# --- CONFIGURAÇÃO DA PÁGINA (FRONTEND) ---
st.set_page_config(
    page_title="Portal de Provas",
    page_icon="🎓",
    layout="wide", # Agora o site usa a tela toda (Widescreen)
    initial_sidebar_state="expanded"
)

# --- ESTILO PERSONALIZADO (CSS SIMPLES) ---
# Isso remove a marca d'água do Streamlit e ajusta margens
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #FF4B4B;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM BANCO DE DADOS ---
@st.cache_resource
def conectar_banco_dados():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("ERRO: Chave 'gcp_service_account' não encontrada no Secrets.")
            st.stop()

        info_conta = dict(st.secrets["gcp_service_account"])
        
        if "private_key" in info_conta:
            info_conta["private_key"] = info_conta["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(info_conta, scopes=scopes)
        client = gspread.authorize(creds)
        
        # --- IMPORTANTE: SEU ID VAI AQUI ---
        ID_PLANILHA = "COLE_AQUI_O_ID_DA_SUA_PLANILHA" 
        
        return client.open_by_key(ID_PLANILHA)
        
    except Exception as e:
        st.error(f"Erro na Conexão: {e}")
        st.stop()

planilha = conectar_banco_dados()

# ==================================================
# 🎨 BARRA LATERAL (SIDEBAR)
# ==================================================
with st.sidebar:
    # Você pode trocar esse link por uma imagem da logo do seu campus
    st.image("https://cdn-icons-png.flaticon.com/512/2997/2997295.png", width=100)
    st.title("Menu Principal")
    
    perfil = st.radio(
        "Selecione seu acesso:", 
        ["🎓 Área do Aluno", "👨‍🏫 Área do Professor"]
    )
    
    st.divider()
    st.info("Sistema de Gestão de Provas\nVersão 2.0")

# ==================================================
# 👨‍🏫 ÁREA DO PROFESSOR (COM SENHA E ABAS)
# ==================================================
if perfil == "👨‍🏫 Área do Professor":
    st.title("👨‍🏫 Painel do Professor")
    
    # Proteção simples por senha
    senha = st.sidebar.text_input("Senha de Acesso", type="password")
    
    # Defina a senha aqui (ex: 1234)
    if senha == "1234": 
        # Cria duas abas para organizar
        tab1, tab2 = st.tabs(["📝 Cadastrar Prova", "📊 Ver Banco de Dados"])
        
        with tab1:
            st.markdown("### Nova Prova")
            with st.container(border=True): # Cria uma caixa bonita ao redor
                with st.form("form_prof"):
                    c1, c2 = st.columns(2)
                    curso = c1.text_input("Curso")
                    turma = c2.text_input("Turma")
                    turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite"])
                    nome_prova = st.text_input("Nome da Prova")
                    gabarito = st.text_input("Gabarito Oficial (Ex: A,B,C)").upper()
                    
                    st.write("") # Espaço vazio
                    if st.form_submit_button("💾 Salvar Prova no Sistema"):
                        if not (curso and turma and nome_prova and gabarito):
                            st.warning("Preencha todos os campos.")
                        else:
                            try:
                                aba = planilha.worksheet("Provas")
                                aba.append_row([curso, turma, turno, nome_prova, gabarito.replace(" ", "")])
                                st.toast("Prova salva com sucesso!", icon="✅") # Notificação flutuante
                            except:
                                st.error("A aba 'Provas' não existe.")
        
        with tab2:
            st.markdown("### Provas Cadastradas")
            if st.button("🔄 Atualizar Lista"):
                try:
                    dados = planilha.worksheet("Provas").get_all_records()
                    st.dataframe(dados, use_container_width=True)
                except:
                    st.error("Erro ao ler dados.")
    
    elif senha != "":
        st.error("Senha incorreta.")
    else:
        st.warning("Por favor, digite a senha no menu lateral para acessar.")

# ==================================================
# 🎓 ÁREA DO ALUNO (VISUAL LIMPO)
# ==================================================
else:
    st.title("🎓 Portal do Aluno")
    st.markdown("Encontre e realize sua prova abaixo.")
    
    # Caixa de Filtros estilizada
    with st.expander("🔍 Clique aqui para filtrar sua turma", expanded=True):
        c1, c2, c3 = st.columns(3)
        f_curso = c1.text_input("Seu Curso")
        f_turma = c2.text_input("Sua Turma")
        f_turno = c3.selectbox("Seu Turno", ["Manhã", "Tarde", "Noite"])
        
        buscar = st.button("🔎 Buscar Provas")

    if buscar:
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
            st.error("Erro de conexão.")

    # Área de Resolução
    if 'provas' in st.session_state and st.session_state['provas']:
        lista = st.session_state['provas']
        
        if not lista:
            st.warning("Nenhuma prova encontrada para esses filtros.")
        else:
            st.divider()
            st.markdown("### ✍️ Realizar Prova")
            
            escolha = st.selectbox("Selecione a prova disponível:", [p['nome_prova'] for p in lista])
            prova = next(p for p in lista if p['nome_prova'] == escolha)
            
            with st.container(border=True):
                st.info(f"Você está realizando: *{prova['nome_prova']}*")
                
                with st.form("resposta"):
                    nome = st.text_input("Seu Nome Completo")
                    st.caption("Digite as letras separadas por vírgula.")
                    resp = st.text_input("Suas Respostas (Ex: A,B,C,D)").upper()
                    
                    if st.form_submit_button("🚀 Entregar Prova"):
                        if nome and resp:
                            gab = prova['gabarito_oficial'].split(',')
                            alu = resp.replace(" ", "").split(',')
                            acertos = sum([1 for i in range(min(len(gab), len(alu))) if gab[i] == alu[i]])
                            total = len(gab)
                            nota = (acertos/total)*100
                            
                            if nota >= 70:
                                st.balloons()
                                st.success(f"*APROVADO!* 🎉\n\nSua nota: {nota:.1f}% ({acertos}/{total} acertos)")
                            else:
                                st.error(f"*REPROVADO* 😔\n\nSua nota: {nota:.1f}% ({acertos}/{total} acertos)")
                            
                            planilha.worksheet("Submissoes").append_row([
                                nome, prova['curso'], prova['turma'], prova['turno'], 
                                prova['nome_prova'], resp, acertos, total
                            ])
