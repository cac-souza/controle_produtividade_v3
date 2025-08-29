import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
import pandas as pd
import plotly.express as px
from modelos import Usuario, RegistroDePontuacao, Tarefa, MetaMensalRegistro
from auth import exigir_login
from helpers import usuarios_visiveis

def pagina_projecao_expiracao(session):
    exigir_login()
    st.title("📆 Projeção de Expiração de Pontos")

    # 🔐 Seleção de usuário com controle de acesso
    nivel_acesso = st.session_state.get("papel", "usuario")
    usuario_logado = session.query(Usuario).get(st.session_state.usuario_id)

    # Define usuário padrão
    usuario_selecionado_id = st.session_state.usuario_id

    if nivel_acesso == "fiscal":
        st.write(f"👤 Consultando dados de: **{usuario_logado.nome}**")

    elif nivel_acesso == "usuario":
        st.write(f"👤 Consultando dados de: **{usuario_logado.nome}**")

    else:
        st.write("👥 Você pode consultar dados de membros da sua equipe.")
        usuarios = usuarios_visiveis(usuario_logado, session)

        if not usuarios:
            st.warning("Nenhum usuário disponível.")
            st.stop()

        nomes_usuarios = {u.id: u.nome for u in usuarios}
        liberar_troca = st.checkbox("🔓 Liberar troca de usuário")

        if liberar_troca and nomes_usuarios:
            usuario_selecionado_id = st.selectbox(
                "Selecionar usuário",
                options=list(nomes_usuarios.keys()),
                format_func=lambda uid: nomes_usuarios[uid]
            )
        else:
            st.write(f"👤 Consultando dados de: **{usuario_logado.nome}**")

    # Define o usuário final
    usuario_id = usuario_selecionado_id

    hoje = datetime.today().date()
    limite = hoje + relativedelta(months=3)

    # Registros que ainda não foram utilizados e expiram nos próximos 3 meses
    registros = session.query(RegistroDePontuacao).filter(
        RegistroDePontuacao.usuario_id == usuario_id,
        RegistroDePontuacao.data_expiracao >= hoje,
        RegistroDePontuacao.data_expiracao <= limite
    ).all()

    tarefas = {t.id: t for t in session.query(Tarefa).filter_by(ativa=True).all()}

    expiracoes = {}
    for r in registros:
        # Ignora registros já utilizados
        utilizado = session.query(MetaMensalRegistro).filter_by(registro_id=r.id).first()
        if utilizado:
            continue

        tarefa = tarefas.get(r.tarefa_id)
        pontos = tarefa.pontos
        mes_expira = r.data_expiracao.strftime('%Y-%m')
        expiracoes[mes_expira] = expiracoes.get(mes_expira, 0) + pontos

    if not expiracoes:
        st.success("✅ Nenhum ponto pendente de expiração nos próximos meses.")
        return

    # Tabela de expirações
    st.warning("⚠️ Pontos que irão expirar se não forem utilizados:")
    df = pd.DataFrame(list(expiracoes.items()), columns=["Mês de Expiração", "Pontos"])
    df = df.sort_values("Mês de Expiração")
    # Garante que o eixo X será categórico e na ordem cronológica
    df["Mês de Expiração"] = pd.Categorical(df["Mês de Expiração"], categories=df["Mês de Expiração"], ordered=True)

    st.dataframe(df, use_container_width=True)

    # Gráfico de barras
    fig = px.bar(
        df,
        x="Mês de Expiração",
        y="Pontos",
        text="Pontos",
        title="Projeção de Expiração de Pontos",
        labels={"Pontos": "Pontos a expirar"},
        color="Pontos",
        color_continuous_scale="oranges"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis=dict(type='category', title="Mês"),
        yaxis=dict(title="Pontos")
    )
    st.plotly_chart(fig, use_container_width=True)

    # Métrica total
    total = df["Pontos"].sum()
    st.metric("Total a expirar nos próximos meses", f"{total:.0f} pts")
