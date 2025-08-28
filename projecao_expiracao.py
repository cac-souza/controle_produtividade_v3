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

    # Usuário logado
    usuario_logado = session.query(Usuario).get(st.session_state.usuario_id)
    usuarios = usuarios_visiveis(usuario_logado, session)
    if not usuarios:
        st.warning("Nenhum usuário disponível.")
        st.stop()

    opcoes = {u.nome: u.id for u in usuarios}
    nome = st.selectbox("👤 Selecione o usuário:", list(opcoes.keys()))
    usuario_id = opcoes[nome]

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
