# calculos.py - 
from datetime import datetime, timedelta

META_DIARIA = 200
BONUS_SEMANAL = 600

def calcular_pontos_totais(tarefas):
    """Soma pontos de uma lista de tarefas."""
    return sum(t.pontos for t in tarefas)

def calcular_excesso(pontos_totais, meta=META_DIARIA):
    """
    Calcula quantos pontos foram feitos acima da meta.
    Retorna 0 se não atingiu a meta.
    """
    return max(0, pontos_totais - meta)

def calcular_bonus_semana(lista_dias):
    """
    Recebe uma lista de totais diários e verifica se houve bônus semanal.
    """
    return sum(lista_dias) >= BONUS_SEMANAL

def pontos_disponiveis_para_uso(pontos_excesso, usados, expirados):
    """
    Retorna quantos pontos de excesso ainda podem ser usados.
    """
    return max(0, pontos_excesso - usados - expirados)

def calcular_expiracao(data_ponto, dias_validade=7):
    """
    Retorna True se o ponto já expirou.
    """
    return datetime.now() > data_ponto + timedelta(days=dias_validade)

