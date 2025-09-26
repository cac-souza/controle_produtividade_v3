# relatorios.py - 
import pandas as pd
from sqlalchemy import text
from db import engine  # Usa a mesma conexão central definida no projeto

def obter_saldo_por_tarefa(usuario_id: int = None, mes: str = None) -> pd.DataFrame:
    """
    Retorna o saldo de pontos por tarefa, agrupado por usuário e mês.

    Parâmetros:
        - usuario_id (int, opcional): filtra por ID do usuário
        - mes (str, opcional): filtra por mês no formato 'YYYY-MM'

    Retorno:
        - DataFrame com colunas: usuario_id, usuario, mes, tarefa_id, tarefa,
          pontos_gerados, pontos_usados, saldo
    """
    query = """
    SELECT
        u.id AS usuario_id,
        u.nome AS usuario,
        strftime('%Y-%m', r.data_execucao) AS mes,
        t.id AS tarefa_id,
        t.descricao AS tarefa,
        SUM(r.pontos) AS pontos_gerados,
        SUM(CASE WHEN r.usado_para_meta = 1 THEN r.pontos ELSE 0 END) AS pontos_usados,
        SUM(r.pontos) - SUM(CASE WHEN r.usado_para_meta = 1 THEN r.pontos ELSE 0 END) AS saldo
    FROM registros_de_pontuacao r
    JOIN usuarios u ON u.id = r.usuario_id
    JOIN tarefas t ON t.id = r.tarefa_id
    GROUP BY usuario_id, mes, tarefa_id
    ORDER BY mes, usuario_id, tarefa_id;
    """

    try:
        # usa conexão direta via engine do SQLAlchemy
        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)
    except Exception as e:
        print("❌ Erro ao consultar o banco:", e)
        return pd.DataFrame()

    # Filtros opcionais
    if usuario_id is not None:
        df = df[df["usuario_id"] == usuario_id]

    if mes:
        mes = str(mes)[:7]  # garante 'YYYY-MM'
        df = df[df["mes"] == mes]

    return df

