import streamlit as st
import bcrypt
import time
from auth import exigir_login
from modelos import Usuario, Setor, Equipe

def pagina_gerenciar_usuarios(session):
    st.title("🔧 Gerenciar Usuários")
    exigir_login()

    usuario_id = st.session_state.usuario_id
    papel = st.session_state.papel.lower()

    # 🔐 Controle de acesso
    if papel == "admin":
        query = session.query(Usuario).filter(Usuario.login != "admin")
    elif papel == "gestor":
        gestor = session.query(Usuario).get(usuario_id)
        query = session.query(Usuario).filter(
            Usuario.login != "admin",
            Usuario.setor_id == gestor.setor_id
        )
    elif papel in ("lider", "chefe"):
        lider = session.query(Usuario).get(usuario_id)
        query = session.query(Usuario).filter(
            Usuario.login != "admin",
            Usuario.equipe_id == lider.equipe_id
        )
    else:
        st.warning("🚫 Você não tem permissão para acessar esta aba.")
        st.stop()

    # 🎯 Filtro de status
    filtro_status = st.radio("Filtrar usuários:", ["Todos", "Apenas ativos"], index=0)
    if filtro_status == "Apenas ativos":
        query = query.filter(Usuario.ativo == True)

    usuarios = query.all()
    setores = session.query(Setor).all()
    equipes = session.query(Equipe).all()

    nomes_papeis = {"fiscal": "Fiscal", "lider": "Chefe", "gestor": "Gestor"}
    opcoes_papel = list(nomes_papeis.keys())

    if not usuarios:
        st.info("Nenhum usuário cadastrado.")
        return

    for usuario in usuarios:
        with st.expander(f"👤 {usuario.nome} ({usuario.login})"):
            form_key = f"form_usuario_{usuario.id}"
            redefinir_key = f"redefinir_{usuario.id}"
            redefinir = st.checkbox("🔁 Redefinir senha", key=redefinir_key)

            if redefinir:
                nova_senha = st.text_input("Nova senha", type="password", key=f"nova_senha_{usuario.id}")
                confirma = st.text_input("Confirmar nova senha", type="password", key=f"confirma_senha_{usuario.id}")
            else:
                nova_senha = confirma = None

            with st.form(form_key):
                novo_nome = st.text_input("Nome", value=usuario.nome, key=f"nome_{usuario.id}").strip()
                nova_matricula = st.text_input("Matrícula", value=usuario.matricula or "", key=f"matricula_{usuario.id}").strip()
                novo_login = st.text_input("Login", value=usuario.login, key=f"login_{usuario.id}").strip()

                papel_usuario = usuario.papel.lower()
                if papel_usuario == "chefe":
                    papel_usuario = "lider"
                papel_idx = opcoes_papel.index(papel_usuario) if papel_usuario in opcoes_papel else 0

                novo_papel_legivel = st.selectbox(
                    "Papel do usuário",
                    options=[nomes_papeis[p] for p in opcoes_papel],
                    index=papel_idx,
                    key=f"papel_{usuario.id}"
                )
                novo_papel = next((p for p, nome in nomes_papeis.items() if nome == novo_papel_legivel), "fiscal")

                if novo_papel in ("fiscal", "gestor") and setores:
                    nomes_setores = [s.nome for s in setores]
                    setor_idx = next((i for i, s in enumerate(setores) if s.id == usuario.setor_id), 0)
                    setor_sel = st.selectbox("Setor", options=nomes_setores, index=setor_idx, key=f"setor_{usuario.id}")
                    novo_setor = next((s for s in setores if s.nome == setor_sel), None)
                else:
                    novo_setor = None

                if novo_papel in ("fiscal", "lider") and equipes:
                    nomes_equipes = [e.nome for e in equipes]
                    equipe_idx = next((i for i, e in enumerate(equipes) if e.id == usuario.equipe_id), 0)
                    equipe_sel = st.selectbox("Equipe", options=nomes_equipes, index=equipe_idx, key=f"equipe_{usuario.id}")
                    nova_equipe = next((e for e in equipes if e.nome == equipe_sel), None)
                else:
                    nova_equipe = None

                desativar = st.checkbox("🚫 Desativar usuário", value=not usuario.ativo, key=f"desativar_{usuario.id}")
                salvar = st.form_submit_button("Salvar alterações")

            if salvar:
                senha_valida = True
                if redefinir:
                    if not nova_senha or len(nova_senha.strip()) < 6:
                        st.error("❌ A senha deve ter ao menos 6 caracteres.")
                        senha_valida = False
                    elif nova_senha != confirma:
                        st.error("❌ As senhas não conferem.")
                        senha_valida = False

                login_em_uso = session.query(Usuario).filter(
                    Usuario.login == novo_login,
                    Usuario.id != usuario.id
                ).first()
                if login_em_uso:
                    st.error("❌ Este login já está em uso por outro usuário.")
                    senha_valida = False

                matricula_em_uso = session.query(Usuario).filter(
                    Usuario.matricula == nova_matricula,
                    Usuario.id != usuario.id
                ).first()
                if matricula_em_uso:
                    st.error("❌ Esta matrícula já está em uso por outro usuário.")
                    senha_valida = False

                if senha_valida:
                    try:
                        usuario.nome = novo_nome
                        usuario.login = novo_login
                        usuario.matricula = nova_matricula
                        usuario.papel = novo_papel
                        usuario.setor_id = novo_setor.id if novo_setor else None
                        usuario.equipe_id = nova_equipe.id if nova_equipe else None
                        usuario.ativo = not desativar

                        if redefinir:
                            hash_senha = bcrypt.hashpw(nova_senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                            usuario.senha_hash = hash_senha
                            usuario.primeiro_acesso = True

                        session.commit()
                        session.refresh(usuario)

                        st.success("✅ Alterações salvas com sucesso!")
                        if redefinir:
                            st.info("🔐 Usuário precisará trocar a senha no próximo login.")

                        time.sleep(2)
                        st.experimental_rerun()

                    except Exception as e:
                        session.rollback()
                        st.error("❌ Não foi possível salvar as alterações. Verifique os dados e tente novamente.")
                        st.exception(e)
