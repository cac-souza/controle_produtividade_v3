# painel.py - 
import streamlit as st
import pandas as pd
import altair as alt
import bcrypt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import time

# Modelos e módulos internos
from modelos import Usuario, Setor, Tarefa, RegistroDePontuacao, Equipe, MetaMensal, MetaMensalRegistro
from carregar_tarefas import carregar_tarefas_padrao
from relatorios import obter_saldo_por_tarefa
from db import SessionLocal, engine
from auth import exigir_login
from helpers import usuarios_visiveis   # ✅ Agora vem do módulo utilitário
from visao_geral import pagina_visao_geral




# -------------------------------
# ⚙️ CONFIGURAÇÃO
# -------------------------------
st.set_page_config(page_title="Painel de Produtividade", layout="wide")
session = SessionLocal()

def inicializar_session_state():
    """Garante que todas as chaves esperadas existam no st.session_state."""
    chaves = [
        "usuario", "usuario_id", "nome", "papel",
        "nivel", "setor_id", "forcar_troca_senha", "equipe_id"
    ]
    for chave in chaves:
        st.session_state.setdefault(chave, None)

inicializar_session_state()

# -------------------------------
# 🔍 FUNÇÕES DE USUÁRIO
# -------------------------------
def buscar_usuario_por_login(login):
    return session.query(Usuario).filter(Usuario.login == login).first()

def buscar_todos_usuarios():
    return [u.login for u in session.query(Usuario).all()]

def buscar_usuarios_por_lider(lider_login):
    return [u.login for u in session.query(Usuario)
            .filter(Usuario.lider == lider_login).all()]

def buscar_usuarios_por_setor(usuario_login):
    usuario = buscar_usuario_por_login(usuario_login)
    if not usuario or not usuario.setor_id:
        return [usuario_login]
    return [
        u.login for u in session.query(Usuario)
        .filter(Usuario.setor_id == usuario.setor_id).all()
    ]

# -------------------------------
# 🔐 AUTENTICAÇÃO / LOGIN
# -------------------------------
def autenticar(login, senha, session):
    usuario = session.query(Usuario).filter_by(login=login).first()

    if not usuario:
        return None, "Usuário não encontrado."
    if not usuario.ativo:
        return None, "Usuário desativado. Fale com o administrador."

    # Detecta hash antigo e força troca de senha
    if not usuario.senha_hash.startswith(("$2a$", "$2b$", "$2y$")):
        st.warning("⚠️ Hash antigo detectado. Redirecionando para troca de senha.")
        st.session_state.usuario_id = usuario.id
        st.session_state.forcar_troca_senha = True
        st.rerun()

    try:
        if bcrypt.checkpw(senha.encode('utf-8'), usuario.senha_hash.encode('utf-8')):
            return usuario, None
        else:
            return None, "Senha incorreta."
    except ValueError:
        return None, "⚠️ Erro ao verificar a senha. Hash inválido."

# -------------------------------
# 🔐 LOGIN
# -------------------------------
if st.session_state.usuario is None and not st.session_state.forcar_troca_senha:
    st.title("🔐 Acesso ao Sistema")

    with st.form("login"):
        login = st.text_input("Login")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        usuario, erro = autenticar(login, senha, session)  # Agora retorna (usuario, erro)

        if erro:
            st.error(erro)

        elif usuario:
            st.session_state.usuario_id = usuario.id
            st.session_state.usuario = usuario.login
            st.session_state.nome = usuario.nome
            st.session_state.papel = usuario.papel
            st.session_state.setor_id = usuario.setor_id
            st.session_state.equipe_id = usuario.equipe_id

            if usuario.primeiro_acesso:
                st.session_state.forcar_troca_senha = True
                st.warning("Este é seu primeiro acesso. Por favor, defina uma nova senha.")
            else:
                st.success(f"Bem-vindo, {usuario.nome}!")

            st.rerun()

    st.stop()

# -------------------------------
# 🔄 TROCA DE SENHA OBRIGATÓRIA
# -------------------------------
if st.session_state.forcar_troca_senha:
    st.title("🔐 Primeiro Acesso - Troca de Senha Obrigatória")
    with st.form("form_troca_senha"):
        nova_senha = st.text_input("Nova senha", type="password")
        confirmar_senha = st.text_input("Confirme a nova senha", type="password")
        confirmar = st.form_submit_button("Salvar")
        if confirmar:
            if len(nova_senha) < 6:
                st.error("❌ A senha deve ter pelo menos 6 caracteres.")
            elif nova_senha != confirmar_senha:
                st.error("❌ As senhas não coincidem.")
            else:
                usuario = session.query(Usuario).get(st.session_state.usuario_id)
                hash_bytes = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt())
                usuario.senha_hash = hash_bytes.decode('utf-8')
                usuario.primeiro_acesso = False
                session.commit()
                st.success("✅ Senha atualizada com sucesso!")
                st.session_state.forcar_troca_senha = None
                st.rerun()
    st.stop()

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.title(f"👤 Usuário: {st.session_state.nome}")
if st.sidebar.button("🔒 Sair"):
    st.session_state.clear()
    st.rerun()

# Simulação visão para admin
papel = st.session_state.papel
if papel == "admin":
    visao_simulada = st.sidebar.selectbox("👓 Simular visão como:", ["Fiscal", "Chefe", "Gestor"], index=1)
    papel = visao_simulada

# -------------------------------
# 📋 PERMISSÕES
# -------------------------------
PERMISSOES = {
    "admin": [
        "Visão Geral", "Cadastrar Produtividade", "Consulta de Pontuação", "Perda de Pontos",
        "Editar Tarefas", "Relatórios", "Cadastro de Usuários", "Gerenciar Usuários", "Gerenciar Equipes"
    ],
    "gestor": [
        "Visão Geral", "Cadastrar Produtividade", "Consulta de Pontuação", "Perda de Pontos",
        "Editar Tarefas", "Relatórios", "Cadastro de Usuários", "Gerenciar Usuários", "Gerenciar Equipes"
    ],
    "lider": [
        "Visão Geral", "Cadastrar Produtividade", "Consulta de Pontuação", "Perda de Pontos",
        "Editar Tarefas", "Cadastro de Usuários", "Gerenciar Usuários"
    ],
    "fiscal": [
        "Visão Geral", "Cadastrar Produtividade", "Consulta de Pontuação", "Perda de Pontos", "Editar Tarefas"
    ]
}
PERMISSOES["chefe"] = PERMISSOES["lider"]

# Normaliza o papel para evitar erros de capitalização ou espaços
papel = papel.strip().lower()
menu = PERMISSOES.get(papel, ["Visão Geral"])

aba = st.sidebar.radio("📂 Navegação", menu)



# Garante equipe_id no session_state
if "equipe_id" not in st.session_state:
    st.session_state.equipe_id = None

def nivel_por_papel(papel: str) -> int:
    """
    Retorna o nível numérico correspondente ao papel do usuário.
    fiscal = 1
    chefe = 2
    gestor/admin = 3
    """
    mapa = {
        "fiscal": 1,
        "chefe": 2,
        "gestor": 3,
        "admin": 3
    }
    return mapa.get(papel.lower(), 0)

# -------------------------------
# 📂 LÓGICA DAS ABAS
# -------------------------------
if aba == "Visão Geral":
    exigir_login()
   # st.subheader("📊 Painel de Visão Geral")
   # st.write("Aqui você pode mostrar gráficos e indicadores principais.")

    # chamada para a página nova
    pagina_visao_geral(session)



elif aba == "Cadastrar Produtividade":
    from cadastrar_produtividade import pagina_cadastrar_produtividade
    pagina_cadastrar_produtividade(session)



elif aba == "Consulta de Pontuação":
    from consulta_pontuacao import pagina_consulta_pontuacao
    pagina_consulta_pontuacao(session)


elif aba == "Editar Tarefas":
    from edicao_tarefas import pagina_edicao_tarefas
    pagina_edicao_tarefas(session)


elif aba == "Projeção de Expiração de Pontos":
    from projecao_expiracao import pagina_projecao_expiracao
    pagina_projecao_expiracao(session)


elif aba == "Relatórios":
    exigir_login()
    st.subheader("📑 Relatórios")
    st.write("Geração e download de relatórios.")
    st.write("EM CONSTRUÇÃO!!")


elif aba == "Cadastro de Usuários":
    from cadastro_usuario import pagina_cadastro_usuario
    pagina_cadastro_usuario(session)


elif aba == "Gerenciar Usuários":
    from gerenciar_usuarios import pagina_gerenciar_usuarios
    pagina_gerenciar_usuarios(session)


elif aba == "Gerenciar Equipes":
    from gerenciar_equipe import pagina_gerenciar_equipes
    pagina_gerenciar_equipes(session)


elif aba == "Perda de Pontos":
    from projecao_expiracao import pagina_projecao_expiracao
    pagina_projecao_expiracao(session)





# -------------------------------
# FIM DO painel.py
# -------------------------------

