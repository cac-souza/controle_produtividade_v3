from datetime import date, datetime, timedelta
import streamlit as st
from modelos import Usuario, RegistroDePontuacao, MetaMensalRegistro, Tarefa
from helpers import usuarios_visiveis


# 🔒 Lista fixa de tarefas
TABELA_TAREFAS_FIXA = [

        ("01", "Plantão Fiscal ½ Período", 15.00),
        ("02", "Diligência Externa", 4.00),
        ("02.1", "Diligência Externa fora do perímetro urbano", 6.00),
        ("03", "Termo de Início de Ação Fiscal", 3.00),
        ("04", "Análise de Documentos Fiscais (por lote de 50)", 4.00),
        ("05", "Demonstrativo de Apuração de Débito Fiscal (por folha)", 4.00),
        ("06", "Notificação", 3.00),
        ("07", "Termo de Ocorrências", 4.00),
        ("08", "Termo de Diligências", 2.00),
        ("09", "Lançamento de ISSQN no Movimento Econômico (por exercício)", 2.00),
        ("10", "Informação/Manifestação em Processo", 5.00),
        ("11", "Elaboração de Relatórios", 5.00),
        ("12", "Publicação de Edital", 4.00),
        ("13", "Outras Atividades não Previstas (por unidade de 1 hora)", 4.00),
        ("14", "Participação em Cursos ou Programas de Treinamento (por ½ período)", 15.00),
        ("15", "Apuração Fiscal c/ resultado para um exercício", 52.00),
        ("15.1", "Apuração Fiscal c/ resultado para exercícios adicionais", 24.00),
        ("16", "Apuração Fiscal s/ resultado para um exercício", 30.00),
        ("16.1", "Apuração Fiscal s/ resultado para exercícios adicionais", 8.00),
        ("17", "Notificação para constituição de crédito tributário (sem A.Infração)", 8.00),
        ("18", "Enquadramento do ISSQN", 8.00),
        ("19", "Atividades Internas (por unidade de 1h)", 4.00),
        ("20", "Auto de Infração", 6.00),
        ("21", "Manifestação em processo de impugnação de Auto de Infração", 8.00),
        ("21.1", "Quando o manifestante não for o autor do Auto de Infração", 12.00),
        ("22", "Chefia ou direção de órgão responsável por atividades previstas nesta tabela (ponto por dia)", 30.00),
        ("98", "Licenciado", 0),
        ("99", "Licenciado", 600)

    ]

def pagina_edicao_tarefas(session):
    st.title("Gerenciar Tarefas Registradas")

    # 🔐 Seleção de usuário com controle de acesso
    nivel_acesso = st.session_state.get("papel", "usuario")
    usuario_logado = session.query(Usuario).get(st.session_state.usuario_id)

    # Se o usuário for fiscal, não mostra troca nem checkbox
    if nivel_acesso == "fiscal":
        usuario_selecionado_id = st.session_state.usuario_id
        st.write(f"👤 Gerenciar Tarefas Registradas para: **{usuario_logado.nome}**")

    else:
        usuarios_visiveis_ao_logado = usuarios_visiveis(usuario_logado, session)
        nomes_usuarios = {u.id: u.nome for u in usuarios_visiveis_ao_logado}

        usuario_selecionado_id = st.session_state.usuario_id

        if nivel_acesso == "usuario":
            st.write(f"👤 Gerenciar Tarefas Registradas para: **{usuario_logado.nome}**")
        else:
            st.write("👥 Você pode gerenciar tarefas para membros da sua equipe.")
            liberar_troca = st.checkbox("🔓 Liberar troca de usuário")

            if liberar_troca and nomes_usuarios:
                usuario_selecionado_id = st.selectbox(
                    "Selecionar usuário",
                    options=list(nomes_usuarios.keys()),
                    format_func=lambda uid: nomes_usuarios[uid]
                )
            else:
                st.write(f"👤 Editando Tarefas Registradas para: **{usuario_logado.nome}**")

    # Define o usuário final e data atual
    usuario_logado = session.query(Usuario).get(usuario_selecionado_id)
    hoje = date.today()

    # 🔍 Filtros
    st.subheader("🔎 Filtros")

    col1, col2 = st.columns(2)
    ano = col1.selectbox("Ano", list(range(hoje.year - 3, hoje.year + 1)), index=3)
    mes = col2.selectbox("Mês", list(range(1, 13)), index=hoje.month - 1)
    inicio_periodo = datetime(ano, mes, 1).date()
    fim_periodo = (datetime(ano, mes, 1).replace(day=28) + timedelta(days=4)).replace(day=1)

    # 🔍 Campo de busca por tarefa
    st.markdown("**Filtrar por tarefa (código ou descrição):**")
    termo_busca = st.text_input("🔎 Digite o código ou parte da descrição", value="")

    # 🔍 Filtra registros válidos para edição/exclusão
    registros_validos = (
        session.query(RegistroDePontuacao)
        .filter(
            RegistroDePontuacao.usuario_id == usuario_logado.id,
            RegistroDePontuacao.data_expiracao >= hoje,
            RegistroDePontuacao.data_execucao >= inicio_periodo,
            RegistroDePontuacao.data_execucao < fim_periodo
        )
        .all()
    )

    registros_editaveis = []
    for r in registros_validos:
        tarefa = r.tarefa
        if not tarefa:
            continue
        if session.query(MetaMensalRegistro).filter_by(registro_id=r.id).first():
            continue

        # Aplica filtro textual
        if termo_busca.strip():
            termo = termo_busca.lower()
            if not (
                termo in tarefa.descricao.lower()
                or termo in tarefa.codigo.lower()
            ):
                continue

        registros_editaveis.append(r)

    if not registros_editaveis:
        st.info("Nenhuma tarefa disponível para edição ou exclusão com os filtros selecionados.")
        return

    # 📋 Lista de registros editáveis
    for r in registros_editaveis:
        tarefa = r.tarefa
        with st.expander(f"{r.data_execucao.strftime('%d/%m/%Y')} - {tarefa.descricao}"):
            st.write(f"**Código:** {tarefa.codigo}")
            st.write(f"**Pontos:** {r.pontos}")
            st.write(f"**Expira em:** {r.data_expiracao.strftime('%d/%m/%Y')}")
            st.write(f"**Processo:** {r.numero_processo or '—'}")

            nova_data = st.date_input("📅 Nova data de execução", value=r.data_execucao, key=f"data_{r.id}")
            novo_processo = st.text_input("🔢 Número do processo", value=r.numero_processo or "", key=f"proc_{r.id}")

            col1, col2 = st.columns(2)
            if col1.button("💾 Salvar alterações", key=f"salvar_{r.id}"):
                r.data_execucao = nova_data
                r.numero_processo = novo_processo
                session.commit()
                st.success("✅ Registro atualizado com sucesso.")
                st.rerun()

            if col2.button("🗑️ Excluir registro", key=f"excluir_{r.id}"):
                session.delete(r)
                session.commit()
                st.warning("🗑️ Registro excluído.")
                st.rerun()
