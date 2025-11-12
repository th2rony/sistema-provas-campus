import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json

# Configuração da aba do navegador
st.set_page_config(page_title="Portal de Provas", page_icon="🎓")

# --- CONEXÃO COM A PLANILHA (MODO SEGURO) ---
@st.cache_resource
def conectar_banco_dados():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # O servidor vai ler a senha do "Cofre" (Secrets), não de um arquivo solto
        info_conta = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info_conta, scope)
        client = gspread.authorize(creds)
        return client.open("Sistema de Provas Acadêmico") # Nome exato da planilha
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        st.stop()

# Conecta assim que o site abre
planilha = conectar_banco_dados()

# --- TELA PRINCIPAL ---
st.title("🎓 Portal Acadêmico")
st.markdown("Bem-vindo ao sistema de provas.")
perfil = st.radio("Quem é você?", ["Sou Professor", "Sou Aluno"], horizontal=True)
st.divider()

# ==================================================
# ÁREA DO PROFESSOR
# ==================================================
if perfil == "Sou Professor":
    st.subheader("Cadastro de Prova")
    
    with st.form("form_nova_prova"):
        col1, col2 = st.columns(2)
        curso = col1.text_input("Curso")
        turma = col2.text_input("Turma")
        turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite"])
        nome_prova = st.text_input("Nome da Prova (Ex: Matemática 1)")
        gabarito = st.text_input("Gabarito Oficial (Ex: A,B,C,D)").upper()
        
        enviar = st.form_submit_button("Salvar Prova")
        
        if enviar:
            if not (curso and turma and nome_prova and gabarito):
                st.warning("Preencha todos os campos!")
            else:
                try:
                    aba = planilha.worksheet("Provas")
                    # Remove espaços do gabarito para evitar erros
                    gabarito_limpo = gabarito.replace(" ", "")
                    aba.append_row([curso, turma, turno, nome_prova, gabarito_limpo])
                    st.success(f"✅ Prova '{nome_prova}' salva com sucesso!")
                except:
                    st.error("Erro ao salvar. Verifique se a aba 'Provas' existe na planilha.")

# ==================================================
# ÁREA DO ALUNO
# ==================================================
else:
    st.subheader("Realizar Prova")
    
    # Filtros de busca
    c1, c2, c3 = st.columns(3)
    f_curso = c1.text_input("Seu Curso")
    f_turma = c2.text_input("Sua Turma")
    f_turno = c3.selectbox("Seu Turno", ["Manhã", "Tarde", "Noite"])
    
    # Botão de busca
    if st.button("🔍 Buscar Provas Disponíveis"):
        try:
            aba = planilha.worksheet("Provas")
            dados = aba.get_all_records()
            df = pd.DataFrame(dados)
            
            if not df.empty:
                # Converte tudo para texto para filtrar sem erros
                df = df.astype(str)
                # Filtra ignorando maiúsculas/minúsculas
                filtro = (
                    (df['curso'].str.lower() == f_curso.lower()) &
                    (df['turma'].str.lower() == f_turma.lower()) &
                    (df['turno'].str.lower() == f_turno.lower())
                )
                # Salva o resultado na memória do navegador
                st.session_state['provas_encontradas'] = df[filtro].to_dict('records')
            else:
                st.warning("Nenhuma prova cadastrada no sistema ainda.")
        except:
            st.error("Erro ao ler planilha. Verifique a aba 'Provas'.")

    # Se encontrou provas, mostra o formulário de resposta
    if 'provas_encontradas' in st.session_state and st.session_state['provas_encontradas']:
        provas = st.session_state['provas_encontradas']
        
        if len(provas) == 0:
            st.warning("Nenhuma prova encontrada para esses dados.")
        else:
            st.write("---")
            # Menu para selecionar a prova
            nomes_provas = [p['nome_prova'] for p in provas]
            escolha = st.selectbox("Selecione a prova:", nomes_provas)
            
            # Pega os dados da prova escolhida
            prova_atual = next(p for p in provas if p['nome_prova'] == escolha)
            
            st.info(f"Você está realizando: *{prova_atual['nome_prova']}*")
            
            with st.form("form_resposta"):
                nome_aluno = st.text_input("Seu Nome Completo")
                respostas = st.text_input("Suas Respostas (Ex: A,B,C,D)").upper()
                
                entregar = st.form_submit_button("✉️ Entregar Prova")
                
                if entregar:
                    if not nome_aluno or not respostas:
                        st.error("Preencha seu nome e respostas.")
                    else:
                        # --- CORREÇÃO AUTOMÁTICA ---
                        gabarito_oficial = prova_atual['gabarito_oficial'].split(',')
                        gabarito_aluno = respostas.replace(" ", "").split(',')
                        
                        acertos = 0
                        total = len(gabarito_oficial)
                        
                        # Compara resposta por resposta
                        for i in range(min(total, len(gabarito_aluno))):
                            if gabarito_oficial[i] == gabarito_aluno[i]:
                                acertos += 1
                        
                        nota = (acertos / total) * 100
                        
                        # Mostra o resultado
                        if nota >= 70:
                            st.balloons()
                            st.success(f"PARABÉNS! Nota: {nota:.1f}% ({acertos}/{total})")
                        else:
                            st.warning(f"Nota: {nota:.1f}% ({acertos}/{total}). Estude mais!")
                            
                        # Salva na planilha
                        try:
                            aba_subs = planilha.worksheet("Submissoes")
                            aba_subs.append_row([
                                nome_aluno,
                                prova_atual['curso'],
                                prova_atual['turma'],
                                prova_atual['turno'],
                                prova_atual['nome_prova'],
                                respostas,
                                acertos,
                                total
                            ])
                        except:
                            st.error("Erro ao salvar nota. Verifique a aba 'Submissoes'.")