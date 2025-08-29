import streamlit as st
from datetime import datetime, timedelta
from auth import exigir_login
from modelos import Usuario, Tarefa, RegistroDePontuacao, MetaMensalRegistro
from helpers import usuarios_visiveis

def pagina_cadastrar_produtividade(session):
    st.title("📝 Novo Registro de Produtividade")
    exigir_login()

    # 🔄 Nível de acesso
    nivel_acesso = st.session_state.papel.lower()

    # 🔍 Buscar tarefas ativas
    tarefas_ativas = session.query(Tarefa).filter_by(ativa=True).all()
    if not tarefas_ativas:
        st.warning("⚠️ Nenhuma tarefa ativa disponível.")
        st.stop()

    # 🔍 Buscar usuários visíveis conforme nível
    usuario_logado = session.query(Usuario).get(st.session_state.usuario_id)
    usuarios_visiveis_lista = usuarios_visiveis(usuario_logado, session)
    nomes_usuarios = {u.id: u.nome for u in usuarios_visiveis_lista}

    # 🔐 Seleção de usuário com controle de acesso
    nivel_acesso = st.session_state.get("papel", "usuario")
    usuario_selecionado_id = st.session_state.usuario_id

    if nivel_acesso == "fiscal":
        st.write(f"👤 Registrando produtividade para: **{st.session_state.usuario}**")
    else:
        st.write("👥 Você pode registrar produtividade para membros da sua equipe.")

        liberar_troca = st.checkbox("🔓 Liberar troca de usuário")

        if liberar_troca and nomes_usuarios:
            usuario_selecionado_id = st.selectbox(
                "Selecionar usuário",
                options=list(nomes_usuarios.keys()),
                format_func=lambda uid: nomes_usuarios[uid]
            )
        else:
            st.write(f"👤 Registrando produtividade para: **{st.session_state.usuario}**")

    # ✅ Seleção da tarefa
    opcoes_tarefa = {
        f"{t.codigo} - {t.descricao}": t
        for t in tarefas_ativas if t.codigo and t.descricao
    }
    tarefa_selecionada = st.selectbox("📌 Selecione a tarefa", options=list(opcoes_tarefa.keys()))
    tarefa = opcoes_tarefa.get(tarefa_selecionada)

    if not tarefa:
        st.error("❌ Tarefa selecionada inválida.")
        st.stop()

    # 📑 Número do Processo (campo obrigatório)
    numero_processo = st.text_input("📑 Número do Processo").strip()

    # 📅 Data de execução
    data_execucao = st.date_input("📅 Data de execução", value=datetime.today())
    st.write(f"Data selecionada: **{data_execucao.strftime('%d/%m/%Y')}**")

    # 🔢 Pontos e quantidade
    st.number_input("Pontos por unidade", value=tarefa.pontos, disabled=True)
    quantidade_realizada = st.number_input("Quantidade realizada", min_value=1, value=1)

    # 🧮 Pontuação total
    total_pontos = tarefa.pontos * quantidade_realizada
    st.number_input("Total de Pontos", value=total_pontos, disabled=True)

    # 💾 Salvar
    if st.button("Salvar", key="salvar_produtividade"):
        if not numero_processo:
            st.error("❌ O campo 'Número do Processo' é obrigatório.")
            st.stop()

        # 🔍 Verificar duplicata
        registro_existente = session.query(RegistroDePontuacao).filter_by(
            usuario_id=usuario_selecionado_id,
            tarefa_id=tarefa.id,
            numero_processo=numero_processo  # precisa existir a coluna numero_processo no modelo
        ).first()

        if registro_existente:
            # Checar se já foi utilizado
            utilizado = session.query(MetaMensalRegistro).filter_by(
                registro_id=registro_existente.id
            ).first()

            situacao = "✅ Pontuação já utilizada" if utilizado else "❌ Pontuação ainda não utilizada"
            st.warning(
                f"🚫 Registro duplicado detectado!\n\n"
                f"- Data do primeiro registro: **{registro_existente.data_execucao.strftime('%d/%m/%Y')}**\n"
                f"- {situacao}"
            )
            st.stop()

        data_expiracao = data_execucao + timedelta(days=365)

        try:
            for _ in range(quantidade_realizada):
                novo_registro = RegistroDePontuacao(
                    usuario_id=usuario_selecionado_id,
                    tarefa_id=tarefa.id,
                    data_execucao=data_execucao,
                    quantidade=1,
                    pontos=tarefa.pontos,
                    data_expiracao=data_expiracao,
                    numero_processo=numero_processo  # novo campo
                )
                session.add(novo_registro)

            session.commit()
            st.success(f"✅ {quantidade_realizada} registro(s) salvo(s) com sucesso!")

        except Exception as e:
            session.rollback()
            st.error("❌ Erro ao salvar registros.")
            st.exception(e)
