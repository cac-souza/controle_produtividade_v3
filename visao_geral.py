# visao_geral.py

import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import streamlit as st

# no topo de visao_geral.py
from modelos import Tarefa, RegistroDePontuacao, MetaMensal, MetaMensalRegistro
from auth import exigir_login

# -------------------------
# Função utilitária
# -------------------------
def agrupar_por_mes(registros, campo_data, campo_valor):
    if not registros:
        return pd.DataFrame(columns=["mes", "valor"])
    dados = []
    for r in registros:
        data = getattr(r, campo_data, None)
        valor = getattr(r, campo_valor, None)
        if data and valor is not None:
            dados.append({
                "mes": data.strftime("%Y-%m"),
                "valor": valor
            })
    df = pd.DataFrame(dados)
    if "mes" not in df.columns or df.empty:
        return pd.DataFrame(columns=["mes", "valor"])
    return df.groupby("mes", as_index=False).sum()

# -------------------------
# Página principal
# -------------------------
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

def pagina_visao_geral(session):
    """Exibe visão geral de produtividade do usuário logado."""
    exigir_login()
    st.title("📊 Sua Produtividade")

    # Parâmetros de tempo e usuário
    hoje = datetime.today()
    inicio_periodo = hoje.replace(day=1) - timedelta(days=365)
    usuario_id = st.session_state.usuario_id

    # Consulta aos registros de pontuação
    registros = session.query(RegistroDePontuacao).filter(
        RegistroDePontuacao.usuario_id == usuario_id,
        RegistroDePontuacao.data_execucao >= inicio_periodo
    ).all()

    # Consulta aos usos confirmados
    usos = session.query(MetaMensal).filter(
        MetaMensal.usuario_id == usuario_id,
        MetaMensal.status == "confirmado"
    ).all()

    # Agrupamento por mês
    pontos_mes = agrupar_por_mes(registros, "data_execucao", "pontos")
    usados_mes = agrupar_por_mes(usos, "data_validacao", "pontos_utilizados") \
        if usos else pd.DataFrame(columns=["mes", "valor"])

    # Renomear para merge
    pontos_mes.rename(columns={"valor": "valor_realizado"}, inplace=True)
    usados_mes.rename(columns={"valor": "valor_usados"}, inplace=True)

    # Merge dos DataFrames
    df_geral = pd.merge(pontos_mes, usados_mes, on="mes", how="outer").fillna(0)
    df_geral = df_geral.sort_values("mes")

    # -------------------------
    # 🔔 Alerta de prescrição de pontos
    # -------------------------
    mes_prescricao_str = (hoje.replace(year=hoje.year - 1)).strftime("%Y-%m")
    linha_prescricao = df_geral[df_geral["mes"] == mes_prescricao_str]

    if not linha_prescricao.empty:
        pontos_realizados_antigos = float(linha_prescricao.iloc[0]["valor_realizado"])

        # Definir intervalo de datas para o mês da prescrição
        inicio_mes_prescricao = date(hoje.year - 1, hoje.month, 1)
        fim_mes_prescricao = inicio_mes_prescricao + relativedelta(months=1)

        # Calcular pontos antigos já usados
        pontos_usados_antigos = 0
        for uso in usos:
            registros_relacionados = (
                session.query(MetaMensalRegistro)
                .join(RegistroDePontuacao)
                .filter(
                    MetaMensalRegistro.meta_id == uso.id,
                    RegistroDePontuacao.usuario_id == usuario_id,
                    RegistroDePontuacao.data_execucao >= inicio_mes_prescricao,
                    RegistroDePontuacao.data_execucao < fim_mes_prescricao
                )
                .all()
            )

            for reg in registros_relacionados:
                tarefa = session.query(Tarefa).get(
                    session.query(RegistroDePontuacao).get(reg.registro_id).tarefa_id
                )
                pontos_usados_antigos += tarefa.pontos

        saldo_prescrever = max(pontos_realizados_antigos - pontos_usados_antigos, 0)

        if saldo_prescrever > 0:
            st.markdown(f"""
            <div style="background-color:#ffe6e6;padding:15px;border-left:5px solid red;">
                <h4 style="color:#b30000;">⚠️ Atenção!</h4>
                <p style="color:#660000;">
                    Você possui <strong>{saldo_prescrever:.0f} pontos</strong> do mês {mes_prescricao_str}
                    que irão prescrever neste mês se não forem utilizados.<br>
                    <em>Use seus pontos antes que expirem!</em>
                </p>
            </div>
            """, unsafe_allow_html=True)

    # -------------------------
    # Conteúdo principal
    # -------------------------
    if df_geral.empty:
        st.info("Ainda não há dados suficientes para exibir sua produtividade nos últimos 12 meses.")
        st.image("https://i.imgur.com/3ZQ3Z9F.png", caption="Produtividade em construção...")
        return

    st.subheader("📅 Pontos por mês")

    # Gráfico com metas
    grafico_df = df_geral.copy()
    grafico_df["meta_minima"] = 200
    grafico_df["meta_ideal"] = 600

    grafico = alt.Chart(grafico_df).mark_line(point=True).encode(
        x=alt.X("mes", title="Mês"),
        y=alt.Y("valor_realizado", title="Pontos Ganhos"),
        color=alt.value("steelblue"),
        tooltip=["mes", "valor_realizado"]
    ).properties(
        title="📈 Produtividade Mensal"
    )

    linha_minima = alt.Chart(grafico_df).mark_line(color="red", strokeDash=[5, 5]).encode(
        x="mes", y="meta_minima"
    )

    linha_ideal = alt.Chart(grafico_df).mark_line(color="green", strokeDash=[2, 4]).encode(
        x="mes", y="meta_ideal"
    )

    st.altair_chart(grafico + linha_minima + linha_ideal, use_container_width=True)

    # Legenda
    with st.expander("📌 Legenda do gráfico"):
        st.markdown("""
        - 🔵 **Linha azul**: Pontos realizados pelo usuário
        - 🔴 **Linha vermelha**: Meta mínima obrigatória (200 pontos)
        - 🟢 **Linha verde**: Meta ideal de produtividade (600 pontos)
        """)

    # Métricas totais
    total_ganhos = df_geral["valor_realizado"].sum()
    total_usados = df_geral["valor_usados"].sum()
    saldo = total_ganhos - total_usados

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Realizado", f"{total_ganhos:.0f} pts")
    col2.metric("Total Usado", f"{total_usados:.0f} pts")
    col3.metric("Saldo Atual", f"{saldo:.0f} pts", delta=f"{saldo:.0f}")
