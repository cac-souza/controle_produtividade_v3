import streamlit as st
import bcrypt
from modelos import Usuario, Setor, Equipe
from auth import exigir_login

def pagina_cadastro_usuario(session):
    st.title("👥 Cadastro de Novo Usuário")
    exigir_login()

    # 🔐 Verificação de permissão - 
    papel_usuario = (st.session_state.papel or "").strip().lower()
    if papel_usuario not in ["admin", "gestor", "lider", "chefe"]:
        st.warning("❌ Você não tem permissão para acessar esta funcionalidade.")
        st.stop()

    # 📝 Formulário de cadastro
    with st.form(key="form_cadastro_usuario"):
        nome = st.text_input("Nome completo")
        matricula = st.text_input("Matrícula (formato: 000000)")
        login = st.text_input("Login (usuário)")
        senha = st.text_input("Senha inicial", type="password")
        confirmar_senha = st.text_input("Confirme a senha", type="password")

        papeis_disponiveis = ["Fiscal", "Chefe", "Gestor"]
        papel_novo_usuario = st.selectbox("Papel do usuário", papeis_disponiveis)
        papel_novo_usuario = papel_novo_usuario.strip().lower()

        setores = session.query(Setor).all()
        setor_dict = {s.nome: s.id for s in setores}
        setor_nome = st.selectbox("Setor (opcional)", options=["Nenhum"] + list(setor_dict.keys()))
        setor_id = setor_dict.get(setor_nome) if setor_nome != "Nenhum" else None

        equipes = session.query(Equipe).all()
        equipe_dict = {e.nome: e.id for e in equipes}
        equipe_nome = st.selectbox("Equipe", options=["Selecionar equipe"] + list(equipe_dict.keys()))
        equipe_id = equipe_dict.get(equipe_nome) if equipe_nome != "Selecionar equipe" else None

        ativo = st.checkbox("Usuário ativo", value=True)
        confirmar = st.form_submit_button("Salvar", type="primary")

    if confirmar:
        erros = []

        if not nome or not login or not senha or not matricula:
            erros.append("Todos os campos obrigatórios devem ser preenchidos.")
        if senha != confirmar_senha:
            erros.append("As senhas não coincidem.")
        if equipe_id is None:
            erros.append("Você deve selecionar uma equipe válida.")

        usuario_existente = session.query(Usuario).filter_by(login=login).first()
        if usuario_existente:
            erros.append(f"Já existe um usuário com esse login: {usuario_existente.nome}")

        usuario_matricula_existente = session.query(Usuario).filter_by(matricula=matricula).first()
        if usuario_matricula_existente:
            erros.append(f"Já existe um usuário com essa matrícula: {usuario_matricula_existente.nome}")

        if erros:
            for erro in erros:
                st.error(f"❌ {erro}")
        else:
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            novo_usuario = Usuario(
                nome=nome,
                matricula=matricula,
                login=login,
                senha_hash=senha_hash,
                papel=papel_novo_usuario,
                setor_id=setor_id,
                equipe_id=equipe_id,
                ativo=ativo,
                primeiro_acesso=True
            )

            session.add(novo_usuario)
            session.commit()
            st.success(f"✅ Usuário '{login}' cadastrado com sucesso!")

