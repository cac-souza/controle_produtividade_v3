# carregar_tarefas.py - 

"""
Módulo para sincronizar as tarefas padrão no banco de dados.
Pode ser executado de forma independente ou importado por outros scripts.
"""

from db import SessionLocal
from modelos import Tarefa

def carregar_tarefas_padrao():
    """Sincroniza o banco com as tarefas padrão: insere, atualiza, reativa e desativa."""
    session = SessionLocal()

    tarefas_padrao = [
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

    codigos_padrao = {codigo for codigo, _, _ in tarefas_padrao}
    tarefas_existentes = session.query(Tarefa).all()

    inseridas = 0
    reativadas = 0
    atualizadas = 0
    desativadas = 0

    # Atualiza ou insere tarefas padrão
    for codigo, descricao, pontos in tarefas_padrao:
        tarefa = session.query(Tarefa).filter_by(codigo=codigo).first()
        if tarefa:
            if not tarefa.ativa:
                tarefa.ativa = True
                reativadas += 1
            if tarefa.descricao != descricao or tarefa.pontos != pontos:
                tarefa.descricao = descricao
                tarefa.pontos = pontos
                atualizadas += 1
        else:
            nova_tarefa = Tarefa(
                codigo=codigo,
                descricao=descricao,
                pontos=pontos,
                ativa=True
            )
            session.add(nova_tarefa)
            inseridas += 1

    # Desativa tarefas que não estão mais na lista padrão
    for tarefa in tarefas_existentes:
        if tarefa.codigo not in codigos_padrao and tarefa.ativa:
            tarefa.ativa = False
            desativadas += 1

    session.commit()
    session.close()

    print(f"✅ {inseridas} tarefas inseridas.")
    print(f"🔄 {reativadas} tarefas reativadas.")
    print(f"✏️ {atualizadas} tarefas atualizadas.")
    print(f"🧹 {desativadas} tarefas desativadas.")

if __name__ == "__main__":
    carregar_tarefas_padrao()


