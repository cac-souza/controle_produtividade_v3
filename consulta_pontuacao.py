import streamlit as st
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from modelos import Usuario, Tarefa, RegistroDePontuacao, MetaMensal, MetaMensalRegistro
from auth import exigir_login
from helpers import usuarios_visiveis
from fpdf import FPDF
import base64
from datetime import timedelta





# ===================================================
# 🔄 Carrega dados principais
# ===================================================
def carregar_dados(session, usuario_id, periodo):
    tarefas = session.query(Tarefa).filter_by(ativa=True).all()
    tarefas_dict = {t.id: t for t in tarefas}

    todos_registros = session.query(RegistroDePontuacao).filter(
        RegistroDePontuacao.usuario_id == usuario_id
    ).all()

    pontos_utilizados = session.query(
        func.coalesce(func.sum(MetaMensal.pontos_utilizados), 0)
    ).filter_by(
        usuario_id=usuario_id,
        ano_mes=periodo,
        status="confirmado"
    ).scalar()

    return tarefas_dict, todos_registros, pontos_utilizados


# ===================================================
# 📋 Exibe tabela de registros
# ===================================================
def exibir_tabela_registros(registros, tarefas_dict, inicio_mes, fim_mes, mostrar_utilizados, chave_prefixo, session):
    selecionados = []
    total = 0

    cabecalho = st.columns([2, 4, 2, 2, 2])
    for i, titulo in enumerate(["Data", "Tarefa", "Pontos", "Expira em", "Selecionar"]):
        cabecalho[i].markdown(f"**{titulo}**")

    for r in registros:
        tarefa = tarefas_dict.get(r.tarefa_id)
        ja_utilizado = session.query(MetaMensalRegistro).filter_by(registro_id=r.id).first()
        expira_este_mes = inicio_mes <= r.data_expiracao < fim_mes
        estilo = "background-color: #fff3cd;" if expira_este_mes else ""

        if not mostrar_utilizados and ja_utilizado:
            continue

        descricao = tarefa.descricao + (" ✅ já utilizado" if ja_utilizado else "")
        linha = st.columns([2, 4, 2, 2, 2])
        linha[0].markdown(f"<div style='{estilo}'>{r.data_execucao.strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)
        linha[1].markdown(f"<div style='{estilo}'>{descricao}</div>", unsafe_allow_html=True)
        linha[2].markdown(f"<div style='{estilo}'>{tarefa.pontos:.0f} pts</div>", unsafe_allow_html=True)
        linha[3].markdown(f"<div style='{estilo}'>{r.data_expiracao.strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)

        if ja_utilizado:
            linha[4].markdown("✅ já utilizado")
        else:
            usar = linha[4].checkbox("", key=f"{chave_prefixo}_{r.id}")
            if usar:
                selecionados.append((r.id, tarefa.pontos))
                total += tarefa.pontos

    return selecionados, total


# ===================================================
# ✅ Confirma registros selecionados
# ===================================================
def confirmar_pontuacao(session, usuario_id, periodo, registros):
    total_selecionado = sum(p for _, p in registros)

    ja_confirmado = session.query(MetaMensal).filter_by(
        usuario_id=usuario_id,
        ano_mes=periodo,
        status="confirmado"
    ).first()

    if ja_confirmado:
        ja_confirmado.pontos_utilizados += total_selecionado
        for reg_id, _ in registros:
            session.add(MetaMensalRegistro(
                meta_id=ja_confirmado.id,
                registro_id=reg_id,
                quantidade_utilizada=1
            ))
    else:
        novo_uso = MetaMensal(
            usuario_id=usuario_id,
            ano_mes=periodo,
            pontos_utilizados=total_selecionado,
            status="confirmado",
            data_validacao=datetime.now().date(),
            validador_id=st.session_state.usuario_id
        )
        session.add(novo_uso)
        session.commit()

        for reg_id, _ in registros:
            session.add(MetaMensalRegistro(
                meta_id=novo_uso.id,
                registro_id=reg_id,
                quantidade_utilizada=1
            ))

    session.commit()
    st.success(f"🎉 {total_selecionado:.0f} pontos confirmados para {periodo}.")
    st.rerun()



# ----------------------------------------------------------------------
# CALCULA SALDO TOTAL
# ----------------------------------------------------------------------
# ✅ Função utilitária para cálculo do saldo total
def calcular_saldo_total(registros, registros_principais, tarefas_dict, inicio_mes, session):
    registros_anteriores = [
        r for r in registros
        if r.data_execucao < inicio_mes
           and r.data_expiracao >= inicio_mes
           and not session.query(MetaMensalRegistro)
               .join(MetaMensal, MetaMensalRegistro.meta_id == MetaMensal.id)
               .filter(
                   MetaMensalRegistro.registro_id == r.id,
                   MetaMensal.status == "confirmado"
               )
               .first()
    ]

    registros_mes = [
        r for r in registros_principais
        if r.data_expiracao >= inicio_mes
           and not session.query(MetaMensalRegistro)
               .join(MetaMensal, MetaMensalRegistro.meta_id == MetaMensal.id)
               .filter(
                   MetaMensalRegistro.registro_id == r.id,
                   MetaMensal.status == "confirmado"
               )
               .first()
    ]

    saldo_anteriores = sum(tarefas_dict[r.tarefa_id].pontos for r in registros_anteriores if r.tarefa_id in tarefas_dict)
    saldo_mes = sum(tarefas_dict[r.tarefa_id].pontos for r in registros_mes if r.tarefa_id in tarefas_dict)

    return saldo_anteriores + saldo_mes





# ----------------------------------------------------------------------
# PDF REGISTRO DOS PONTOS
# ----------------------------------------------------------------------
def gerar_pdf(tarefas_dict, periodo, nome_fiscal, session):
    from modelos import MetaMensalRegistro, RegistroDePontuacao, MetaMensal, Usuario
    from datetime import datetime, timedelta
    from fpdf import FPDF
    import streamlit as st
    import base64

    class PDF(FPDF):
        def __init__(self, periodo, nome_fiscal):
            super().__init__()
            self.periodo = periodo
            self.nome_fiscal = nome_fiscal

        def header(self):
            if self.page_no() > 1:
                self.set_font("Arial", '', 9)
                self.cell(
                    0, 8,
                    f"Continuação - Registros de Pontuação {self.periodo} ({self.nome_fiscal})",
                    0, 1, 'C'
                )
                self.ln(2)

    # --------------------------------
    # 🆔 Identifica usuários permitidos
    # --------------------------------
    usuario_logado = session.query(Usuario).get(st.session_state.usuario_id)
    usuario_selecionado_id = st.session_state.get("usuario_selecionado_id", usuario_logado.id)

    fiscal = session.query(Usuario).filter(Usuario.nome == nome_fiscal).first()
    if fiscal:
        ids_permitidos = [u.id for u in fiscal.liderados] + [fiscal.id]
    else:
        ids_permitidos = [usuario_selecionado_id]

    # --------------------------------
    # Intervalo do mês
    # --------------------------------
    inicio_mes = datetime.strptime(periodo, "%Y-%m").date().replace(day=1)
    fim_mes = (inicio_mes + timedelta(days=32)).replace(day=1)

    # --------------------------------
    # Consulta registros
    # --------------------------------
    registros_mes_utilizados = (
        session.query(MetaMensalRegistro)
        .join(RegistroDePontuacao)
        .join(MetaMensal)
        .filter(
            RegistroDePontuacao.data_execucao >= inicio_mes,
            RegistroDePontuacao.data_execucao < fim_mes,
            MetaMensal.ano_mes == periodo,
            MetaMensal.status == "confirmado",
            RegistroDePontuacao.usuario_id.in_(ids_permitidos)
        )
        .all()
    )

    registros_antigos_utilizados = (
        session.query(MetaMensalRegistro)
        .join(RegistroDePontuacao)
        .join(MetaMensal)
        .filter(
            RegistroDePontuacao.data_execucao < inicio_mes,
            MetaMensal.ano_mes == periodo,
            MetaMensal.status == "confirmado",
            RegistroDePontuacao.usuario_id.in_(ids_permitidos)
        )
        .all()
    )

    if not registros_mes_utilizados and not registros_antigos_utilizados:
        st.warning("Nenhum registro utilizado no período informado.")
        return

    # --------------------------------
    # Configura PDF
    # --------------------------------
    pdf = PDF(periodo, nome_fiscal)
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    col_w = [30, 30, 90, 30]
    line_h = 8

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Registros de Pontuação - {periodo}", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 8, f"Fiscal responsável: {nome_fiscal}", ln=True, align='C')
    pdf.ln(5)

    def imprime_cabecalho_tabela():
        pdf.set_font("Arial", 'B', 11)
        headers = ["DATA", "Nº PROC", "DESCRIÇÃO", "PONTOS"]
        for w, head in zip(col_w, headers):
            pdf.cell(w, line_h, head, border=1, align='C')
        pdf.ln()

    def quebra_antes(altura):
        if pdf.get_y() + altura > pdf.page_break_trigger:
            pdf.add_page()
            imprime_cabecalho_tabela()

    def escreve_linha(data_txt, proc_txt, desc_txt, pts_txt):
        pdf.set_font("Arial", '', 11)
        linhas_data = len(pdf.multi_cell(col_w[0], line_h, data_txt, border=0, split_only=True))
        linhas_proc = len(pdf.multi_cell(col_w[1], line_h, proc_txt, border=0, split_only=True))
        linhas_desc = len(pdf.multi_cell(col_w[2], line_h, desc_txt, border=0, split_only=True))
        linhas_pts  = len(pdf.multi_cell(col_w[3], line_h, pts_txt, border=0, split_only=True))

        altura_linha = max(linhas_data, linhas_proc, linhas_desc, linhas_pts) * line_h
        quebra_antes(altura_linha)

        x, y = pdf.get_x(), pdf.get_y()
        pdf.rect(x, y, col_w[0], altura_linha)
        pdf.rect(x + col_w[0], y, col_w[1], altura_linha)
        pdf.rect(x + col_w[0] + col_w[1], y, col_w[2], altura_linha)
        pdf.rect(x + col_w[0] + col_w[1] + col_w[2], y, col_w[3], altura_linha)

        pdf.set_xy(x, y)
        pdf.multi_cell(col_w[0], line_h, data_txt, border=0)
        pdf.set_xy(x + col_w[0], y)
        pdf.multi_cell(col_w[1], line_h, proc_txt, border=0)
        pdf.set_xy(x + col_w[0] + col_w[1], y)
        pdf.multi_cell(col_w[2], line_h, desc_txt, border=0)
        pdf.set_xy(x + col_w[0] + col_w[1] + col_w[2], y)
        pdf.multi_cell(col_w[3], line_h, pts_txt, border=0, align='C')

        pdf.set_y(y + altura_linha)

    def escreve_total_bloco(total):
        quebra_antes(line_h)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(sum(col_w[:-1]), line_h, "TOTAL", border=1)
        pdf.cell(col_w[-1], line_h, f"{total:.0f}", border=1, ln=True)
        pdf.ln(5)

    def escreve_bloco(titulo, registros):
        total = 0
        if not registros:
            return total
        quebra_antes(line_h * 2)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, line_h, titulo, ln=True)
        imprime_cabecalho_tabela()
        linhas = []
        for r in registros:
            reg = r.registro
            tarefa = tarefas_dict.get(reg.tarefa_id)
            desc = tarefa.descricao if tarefa else "(Tarefa não encontrada)"
            pts = tarefa.pontos if tarefa else 0
            linhas.append((reg.data_execucao, reg.numero_processo or "", desc, pts))
            total += pts
        linhas.sort(key=lambda x: x[0])
        for linha in linhas:
            escreve_linha(
                linha[0].strftime("%d/%m/%Y"),
                linha[1],
                linha[2],
                f"{linha[3]:.0f}"
            )
        escreve_total_bloco(total)
        return total

    # Grupos e totais
    total_mes = escreve_bloco("Grupo 1 - Utilizados Mês", registros_mes_utilizados)
    total_antigos = escreve_bloco("Grupo 2 - Utilizados Antigos", registros_antigos_utilizados)

    quebra_antes(line_h)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(sum(col_w[:-1]), line_h, "TOTAL GERAL", border=1)
    pdf.cell(col_w[-1], line_h, f"{total_mes + total_antigos:.0f}", border=1, ln=True)

    # Saída final
    pdf_data = pdf.output(dest="S")
    pdf_bytes = pdf_data.encode("latin1") if isinstance(pdf_data, str) else bytes(pdf_data)

    st.download_button(
        label="📥 Baixar PDF",
        data=pdf_bytes,
        file_name=f"registros_{periodo}_{nome_fiscal}.pdf",
        mime="application/pdf"
    )

    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px"></iframe>',
        unsafe_allow_html=True
    )


# ----------------------------------------------------------------------
# PDF RELATÓRIO DE PRODUTIVIDADE
# ----------------------------------------------------------------------
def gerar_pdf_pontos_totais_detalhado(tarefas_dict, registros_utilizados, registros, registros_principais, pontos_expirados, periodo, usuario_obj, inicio_mes, session):
    from fpdf import FPDF
    import streamlit as st
    import base64
    from collections import defaultdict

    MESES_PT = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
        "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
        "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
    }

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

    class PDF(FPDF):
        def __init__(self):
            super().__init__('L', 'mm', 'A4')
            self.set_auto_page_break(auto=False)

        def header(self):
            self.set_font("Arial", 'BU', 12)
            self.cell(0, 8, "RELATÓRIO MENSAL DE PRODUTIVIDADE - FISCAL DE TRIBUTOS", ln=True, align='C')

    pdf = PDF()
    pdf.set_margins(10, 10, 10)
    pdf.add_page()

    nome = usuario_obj.nome
    matricula = usuario_obj.matricula or "000000"
    mes_num = periodo.split("-")[1]
    ano = periodo.split("-")[0]
    mes_formatado = f"{MESES_PT.get(mes_num, mes_num)}/{ano}"

    pdf.set_font("Arial", '', 10)
    pdf.cell(25, 5, "Fiscal:", ln=0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 5, nome, ln=0)

    pdf.set_font("Arial", '', 10)
    pdf.cell(30, 5, "Matrícula nº", ln=0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 5, matricula, ln=0)

    pdf.set_font("Arial", '', 10)
    pdf.cell(15, 5, "Mês:", ln=0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 5, mes_formatado, ln=1)

    pdf.ln(3)

    # 🧮 Contagem de tarefas utilizadas
    quantidades_por_codigo = defaultdict(int)
    for r in registros_utilizados:
        tarefa = tarefas_dict.get(r.tarefa_id)
        if tarefa and tarefa.codigo:
            quantidades_por_codigo[tarefa.codigo] += r.quantidade or 1

    # 🧾 Tabela de tarefas
    col_w = [25, 160, 20, 20, 25]
    line_h = 5

    pdf.set_font("Arial", 'B', 8)
    headers = ["Código", "Descrição", "Pontos", "Quant", "Total"]
    for w, head in zip(col_w, headers):
        pdf.cell(w, line_h, head, border=1, align='C')
    pdf.ln()

    total_mensal = 0
    pdf.set_font("Arial", '', 8)
    for codigo, descricao, pontos in TABELA_TAREFAS_FIXA:
        qtd = quantidades_por_codigo.get(codigo, 0)
        total = pontos * qtd
        total_mensal += total
        pdf.cell(col_w[0], line_h, codigo, border=1)
        pdf.cell(col_w[1], line_h, descricao, border=1)
        pdf.cell(col_w[2], line_h, f"{pontos:.0f}", border=1, align='C')
        pdf.cell(col_w[3], line_h, f"{qtd}", border=1, align='C')
        pdf.cell(col_w[4], line_h, f"{total:.0f}", border=1, align='C')
        pdf.ln()

    # ✅ Cálculo do saldo total usando função utilitária
    saldo_total = calcular_saldo_total(registros, registros_principais, tarefas_dict, inicio_mes, session)

    # 📊 Resumo final
    resultado_mes = total_mensal + saldo_total - pontos_expirados
    excedente = resultado_mes - 200
    a_receber = min(400, max(0, excedente))
    saldo_transportar = max(0, resultado_mes - total_mensal)

    # 📊 Tabela de resumo
    resumo_col1 = col_w[2] + col_w[3]
    resumo_col2 = col_w[4]

    def resumo_linha(label, valor, negrito=False):
        fonte = 'B' if negrito else ''
        pdf.set_font("Arial", fonte, 8)
        pdf.set_x(pdf.l_margin + col_w[0] + col_w[1])
        pdf.cell(resumo_col1, line_h, label, border=1)
        pdf.cell(resumo_col2, line_h, f"{valor:.0f} pts", border=1, align='C', ln=True)

    resumo_linha("Total Mensal", total_mensal, negrito=True)
    resumo_linha("Saldo", saldo_total)
    resumo_linha("Pontos Cancelados", pontos_expirados)
    resumo_linha("Resultado do Mês", resultado_mes)
    resumo_linha("A Receber", a_receber, negrito=True)
    resumo_linha("Saldo a Transportar", saldo_transportar, negrito=True)

    # 📤 Exportação
    pdf_data = pdf.output(dest="S")
    pdf_bytes = pdf_data.encode("latin1") if isinstance(pdf_data, str) else bytes(pdf_data)

    st.download_button(
        label="📥 Baixar PDF Relatório de Pontos Totais",
        data=pdf_bytes,
        file_name=f"relatorio_produtividade_{periodo}_{usuario_obj.nome}.pdf",
        mime="application/pdf"
    )

    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600px"></iframe>',
        unsafe_allow_html=True
    )


# ===================================================
# 🧩 Página principal
# ===================================================
def pagina_consulta_pontuacao(session):
    exigir_login()
    st.session_state.session = session
    st.title("📄 Consulta de Pontuação")

    # 🔐 Seleção de usuário com controle de acesso
    nivel_acesso = st.session_state.get("papel", "usuario")
    usuario_logado = session.query(Usuario).get(st.session_state.usuario_id)

    usuarios = usuarios_visiveis(usuario_logado, session)
    if not usuarios:
        st.warning("Nenhum usuário disponível para consulta.")
        st.stop()

    nomes_usuarios = {u.id: u.nome for u in usuarios}
    usuario_selecionado_id = st.session_state.usuario_id

    if nivel_acesso == "usuario":
        st.write(f"👤 Consultando pontuação de: **{st.session_state.usuario}**")
    else:
        st.write("👥 Você pode consultar pontuação de membros da sua equipe.")
        liberar_troca = st.checkbox("🔓 Liberar troca de usuário")

        if liberar_troca and nomes_usuarios:
            usuario_selecionado_id = st.selectbox(
                "Selecionar usuário",
                options=list(nomes_usuarios.keys()),
                format_func=lambda uid: nomes_usuarios[uid]
            )
        else:
            st.write(f"👤 Consultando pontuação de: **{st.session_state.usuario}**")

    usuario_id = usuario_selecionado_id
    usuario_obj = session.query(Usuario).get(usuario_id)
    nome_fiscal = usuario_obj.nome

    hoje = datetime.today().date()
    ano = st.selectbox("📅 Ano", list(range(hoje.year - 3, hoje.year + 1)), index=3)
    mes = st.selectbox("🗓️ Mês", list(range(1, 13)), index=hoje.month - 1)
    periodo = f"{ano}-{mes:02d}"
    inicio_mes = datetime(ano, mes, 1).date()
    fim_mes = (datetime(ano, mes, 1) + relativedelta(months=1)).date()

    # chamada corrigida: só 3 argumentos
    tarefas_dict, registros, _ = carregar_dados(session, usuario_id, periodo)

    # -------------------------
    # 🔍 Aviso amarelo: pontos que expiram no mês
    # -------------------------
    expirando_este_mes = [
        r for r in registros
        if inicio_mes <= r.data_expiracao < fim_mes
           and not (
               session.query(MetaMensalRegistro)
                      .join(MetaMensal, MetaMensalRegistro.meta_id == MetaMensal.id)
                      .filter(
                          MetaMensalRegistro.registro_id == r.id,
                          MetaMensal.status == "confirmado"
                      )
                      .first()
           )
    ]
    pontos_expirando = sum(r.pontos for r in expirando_este_mes)
    if expirando_este_mes:
        st.markdown(
            f"<div style='background-color:#fff3cd;padding:12px;border-radius:6px;'>"
            f"⚠️ <strong>{len(expirando_este_mes)}</strong> registro(s) irão expirar até "
            f"<strong>{fim_mes.strftime('%d/%m/%Y')}</strong>, totalizando "
            f"<strong>{pontos_expirando:.0f} pontos</strong>."
            f"</div>",
            unsafe_allow_html=True
        )

    # -------------------------
    # 🔍 Separação dos registros
    # -------------------------
    registros_principais = [
        r for r in registros
        if r.data_execucao.year == ano and r.data_execucao.month == mes
    ]

    mostrar_utilizados = st.toggle("📂 Mostrar registros já utilizados", value=False)
    mostrar_anteriores = st.toggle("📂 Mostrar registros anteriores não utilizados e não expirados", value=False)

    if mostrar_anteriores:
        filtro_mes_antigo = st.radio(
            "📅 Filtrar registros anteriores por:",
            ["Todos", "Selecionar mês"],
            horizontal=True
        )

        if filtro_mes_antigo == "Selecionar mês":
            ano_antigo = st.selectbox("Ano do registro anterior", list(range(hoje.year - 3, hoje.year + 1)), index=3,
                                      key="ano_antigo")
            mes_antigo = st.selectbox("Mês do registro anterior", list(range(1, 13)), index=hoje.month - 2,
                                      key="mes_antigo")
            inicio_filtro = datetime(ano_antigo, mes_antigo, 1).date()
            fim_filtro = (datetime(ano_antigo, mes_antigo, 1) + relativedelta(months=1)).date()
        else:
            inicio_filtro = None
            fim_filtro = None

        registros_anteriores = [
            r for r in registros
            if r.data_execucao < inicio_mes
               and r.data_expiracao >= inicio_mes  # ← exclui registros expirados
               and (
                       filtro_mes_antigo == "Todos"
                       or (inicio_filtro <= r.data_execucao < fim_filtro)
               )
               and (
                       mostrar_utilizados
                       or not session.query(MetaMensalRegistro)
                       .join(MetaMensal, MetaMensalRegistro.meta_id == MetaMensal.id)
                       .filter(
                   MetaMensalRegistro.registro_id == r.id,
                   MetaMensal.status == "confirmado"
               )
                       .first()
               )
        ]

    else:
        registros_anteriores = []

    registros_selecionados = []
    total_selecionado = 0

    if mostrar_anteriores:
        st.subheader("📂 Registros anteriores")
        regs_ant_sel, total_ant = exibir_tabela_registros(
            registros_anteriores, tarefas_dict, inicio_mes, fim_mes,
            mostrar_utilizados, "ant", session  # session adicionado
        )
        registros_selecionados.extend(regs_ant_sel)
        total_selecionado += total_ant

    st.subheader("📋 Registros do mês atual")
    regs_mes_sel, total_mes = exibir_tabela_registros(
        registros_principais, tarefas_dict, inicio_mes, fim_mes,
        mostrar_utilizados, "sel", session  # session adicionado
    )
    registros_selecionados.extend(regs_mes_sel)
    total_selecionado += total_mes

    # -------------------------
    # 📊 Cálculos de métricas
    # -------------------------
    total_realizado = sum(
        t.pontos for r in registros_principais
        if (t := tarefas_dict.get(r.tarefa_id))
    )

    registros_mes_utilizados = (
        session.query(MetaMensalRegistro)
        .join(RegistroDePontuacao, MetaMensalRegistro.registro_id == RegistroDePontuacao.id)
        .join(MetaMensal, MetaMensalRegistro.meta_id == MetaMensal.id)
        .filter(
            RegistroDePontuacao.usuario_id == usuario_id,
            RegistroDePontuacao.data_execucao >= inicio_mes,
            RegistroDePontuacao.data_execucao < fim_mes,
            MetaMensal.usuario_id == usuario_id,
            MetaMensal.ano_mes == periodo,
            MetaMensal.status == "confirmado"
        )
        .all()
    )
    pontos_utilizados_atual = sum(
        tarefas_dict[
            session.query(RegistroDePontuacao).get(r.registro_id).tarefa_id
        ].pontos
        for r in registros_mes_utilizados
    )

    registros_antigos_utilizados = (
        session.query(MetaMensalRegistro)
        .join(RegistroDePontuacao, MetaMensalRegistro.registro_id == RegistroDePontuacao.id)
        .join(MetaMensal, MetaMensalRegistro.meta_id == MetaMensal.id)
        .filter(
            RegistroDePontuacao.usuario_id == usuario_id,
            RegistroDePontuacao.data_execucao < inicio_mes,
            MetaMensal.usuario_id == usuario_id,
            MetaMensal.ano_mes == periodo,
            MetaMensal.status == "confirmado"
        )
        .all()
    )
    utilizados_antigos = sum(
        tarefas_dict[
            session.query(RegistroDePontuacao).get(r.registro_id).tarefa_id
        ].pontos
        for r in registros_antigos_utilizados
    )

    total_utilizado = pontos_utilizados_atual + utilizados_antigos
    saldo_mensal = total_realizado - pontos_utilizados_atual

    # -------------------------
    # 🎨 Exibição das métricas
    # -------------------------
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <style>
        div[data-testid="stMetricValue"] { font-size: 20px; }
        div[data-testid="stMetricLabel"] { font-size: 18px; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Realizado Mês", f"{total_realizado:.0f} pts")
    c2.metric("Utilizados Mês", f"{pontos_utilizados_atual:.0f} pts")
    c3.metric("Saldo Mensal", f"{saldo_mensal:.0f} pts")
    c4.metric("Selecionados", f"{total_selecionado:.0f} pts")
    c5.metric("Utilizados Antigos", f"{utilizados_antigos:.0f} pts")
    c6.metric("Total Utilizado", f"{total_utilizado:.0f} pts")

    # -------------------------
    # ✅ Ações
    # -------------------------
    if st.button("✅ Confirmar Pontuação para Relatório"):
        if not registros_selecionados:
            st.warning("Nenhum registro selecionado.")
        else:
            registros_ja_usados = [
                registro_id
                for (registro_id, _) in registros_selecionados
                if session.query(MetaMensalRegistro)
                          .join(MetaMensal, MetaMensalRegistro.meta_id == MetaMensal.id)
                          .filter(
                              MetaMensalRegistro.registro_id == registro_id,
                              MetaMensal.status == "confirmado"
                          )
                          .first()
            ]
            if registros_ja_usados:
                st.warning("Um ou mais registros selecionados já foram utilizados.")
            else:
                confirmar_pontuacao(session, usuario_id, periodo, registros_selecionados)

    if st.button("📄 Gerar PDF Tarefas Utilizadas"):
        gerar_pdf(tarefas_dict, periodo, nome_fiscal, session)

    if st.button("📄 Gerar PDF Pontos Totais"):
        registros_utilizados = registros_mes_utilizados + registros_antigos_utilizados
        usuario_obj = session.query(Usuario).get(usuario_id)

        gerar_pdf_pontos_totais_detalhado(
            tarefas_dict=tarefas_dict,
            registros_utilizados=[r.registro for r in registros_utilizados],
            registros=registros,
            registros_principais=registros_principais,
            pontos_expirados=sum(r.pontos for r in expirando_este_mes),
            periodo=periodo,
            usuario_obj=usuario_obj,
            inicio_mes=inicio_mes,
            session=session
        )





