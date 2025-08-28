import streamlit as st
from modelos import Equipe, Usuario
from auth import exigir_login


def pagina_gerenciar_equipes(session):
    st.title("👥 Gerenciamento de Equipes")

    # Limpa o campo antes de renderizar o widget
    if st.session_state.get("limpar_input_nova_equipe", False):
        st.session_state.pop("input_nova_equipe", None)
        st.session_state["limpar_input_nova_equipe"] = False
        st.rerun()

    # Formulário para adicionar nova equipe
    with st.form("form_equipes"):
        nome_equipe = st.text_input("Nome da nova equipe", key="input_nova_equipe")
        cadastrar = st.form_submit_button("Criar Equipe")

        if cadastrar:
            nome_limpo = nome_equipe.strip()
            if not nome_limpo:
                st.warning("Informe um nome para a equipe.")
            elif session.query(Equipe).filter_by(nome=nome_limpo).first():
                st.error("Já existe uma equipe com esse nome.")
            else:
                nova = Equipe(nome=nome_limpo)
                session.add(nova)
                session.commit()
                st.success("Equipe cadastrada com sucesso!")

                # Marca para limpar o campo na próxima execução
                st.session_state["limpar_input_nova_equipe"] = True
                st.rerun()

    # Exibir equipes já cadastradas
    st.subheader("📋 Equipes já cadastradas")
    equipes = session.query(Equipe).all()

    if equipes:
        for equipe in equipes:
            with st.form(f"form_equipe_{equipe.id}"):
                col1, col2, col3 = st.columns([6, 1, 1])
                col1.markdown(f"**{equipe.nome}**")
                editar = col2.form_submit_button("✏️ Editar")
                excluir = col3.form_submit_button("🗑️ Excluir")

                if editar:
                    st.session_state[f"editando_{equipe.id}"] = True
                    st.rerun()

                if excluir:
                    fiscais = session.query(Usuario).filter_by(equipe_id=equipe.id).count()
                    if fiscais > 0:
                        st.error("Não é possível excluir: há usuários vinculados a esta equipe.")
                    else:
                        session.delete(equipe)
                        session.commit()
                        st.success("Equipe excluída com sucesso!")
                        st.rerun()

            # Campo de edição de equipe
            if st.session_state.get(f"editando_{equipe.id}", False):
                st.markdown("---")
                st.subheader(f"✏️ Editar equipe: {equipe.nome}")
                with st.form(f"form_edicao_{equipe.id}"):
                    novo_nome = st.text_input(
                        "Novo nome da equipe",
                        value=equipe.nome,
                        key=f"novo_nome_{equipe.id}"
                    )
                    confirmar = st.form_submit_button("Salvar")

                    if confirmar:
                        nome_editado = novo_nome.strip()
                        if not nome_editado:
                            st.warning("O nome não pode estar vazio.")
                        elif nome_editado == equipe.nome:
                            st.info("O nome não foi alterado.")
                        elif session.query(Equipe).filter_by(nome=nome_editado).first():
                            st.error("Já existe uma equipe com esse nome.")
                        else:
                            equipe.nome = nome_editado
                            session.commit()
                            st.success("Nome da equipe atualizado!")
                            st.session_state[f"editando_{equipe.id}"] = False
                            st.rerun()
    else:
        st.info("Nenhuma equipe cadastrada ainda.")
