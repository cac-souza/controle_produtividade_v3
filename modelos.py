from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey,
    Float, Boolean, Text, func
)
from sqlalchemy.orm import declarative_base, relationship
from enum import Enum

# Base declarativa usada pelo Alembic - 
Base = declarative_base()

# ----------------------------
# 🎯 Enum para Status da Meta
# ----------------------------
class StatusMeta(str, Enum):
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    REJEITADO = "rejeitado"

# ----------------------------
# 📁 Setores
# ----------------------------
class Setor(Base):
    __tablename__ = 'setores'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)

    usuarios = relationship('Usuario', back_populates='setor')

    def __repr__(self):
        return f"<Setor(id={self.id}, nome='{self.nome}')>"

# ----------------------------
# 👥 Equipes
# ----------------------------
class Equipe(Base):
    __tablename__ = "equipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, unique=True, nullable=False)

    usuarios = relationship("Usuario", back_populates="equipe")

    def __repr__(self):
        return f"<Equipe(id={self.id}, nome='{self.nome}')>"

# ----------------------------
# 🙋‍♂️ Usuários
# ----------------------------
class Usuario(Base):
    __tablename__ = 'usuarios'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    matricula = Column(String(20), unique=True, nullable=True)
    login = Column(String(120), unique=True, nullable=False)  # usado para login no painel
    senha_hash = Column(String(255), nullable=False)
    papel = Column(String, nullable=False, default="fiscal")  # admin, gestor, fiscal etc.
    setor_id = Column(Integer, ForeignKey('setores.id'), nullable=True)
    equipe_id = Column(Integer, ForeignKey('equipes.id'), nullable=True)
    lider_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    ativo = Column(Boolean, default=True)
    primeiro_acesso = Column(Boolean, default=True)

    setor = relationship('Setor', back_populates='usuarios')
    equipe = relationship('Equipe', back_populates='usuarios')
    registros = relationship('RegistroDePontuacao', back_populates='usuario')
    metas = relationship(
        'MetaMensal',
        back_populates='usuario',
        foreign_keys='MetaMensal.usuario_id'
    )
    metas_validadas = relationship(
        'MetaMensal',
        back_populates='validador',
        foreign_keys='MetaMensal.validador_id'
    )
    lider = relationship('Usuario', remote_side=[id], backref='liderados')
    tarefas = relationship('Tarefa', back_populates='usuario', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Usuario(id={self.id}, nome='{self.nome}', login='{self.login}')>"

# ----------------------------
# 📂 Projetos
# ----------------------------
class Projeto(Base):
    __tablename__ = "projetos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(150), nullable=False)
    descricao = Column(Text)
    data_criacao = Column(Date, default=func.current_date())

    tarefas = relationship("Tarefa", back_populates="projeto", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Projeto(nome={self.nome})>"

# ----------------------------
# ✅ Tarefas
# ----------------------------
class Tarefa(Base):
    __tablename__ = "tarefas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(10), unique=True, nullable=False)  # << adicionado
    descricao = Column(Text)
    pontos = Column(Float, nullable=False)  # << Campo adicionado
    data_inicio = Column(DateTime, default=func.now())
    data_fim = Column(DateTime)
    status = Column(String(50), default="pendente")  # pendente, em_andamento, concluída
    prioridade = Column(Integer, default=1)  # 1=baixa, 2=média, 3=alta
    ativa = Column(Boolean, default=True)  # ✅ nova coluna

    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=True)

    usuario = relationship("Usuario", back_populates="tarefas")
    projeto = relationship("Projeto", back_populates="tarefas")
    apontamentos = relationship("Apontamento", back_populates="tarefa", cascade="all, delete-orphan")
    registros = relationship('RegistroDePontuacao', back_populates='tarefa')

    def __repr__(self):
        return f"<Tarefa(titulo={self.titulo}, status={self.status})>"

# ----------------------------
# ⏱ Apontamentos
# ----------------------------
class Apontamento(Base):
    __tablename__ = "apontamentos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tarefa_id = Column(Integer, ForeignKey("tarefas.id"), nullable=False)
    data = Column(Date, default=func.current_date())
    horas = Column(Float, nullable=False)

    tarefa = relationship("Tarefa", back_populates="apontamentos")

    def __repr__(self):
        return f"<Apontamento(tarefa_id={self.tarefa_id}, horas={self.horas})>"

# ----------------------------
# ⭐ Registro de Pontuação
# ----------------------------
class RegistroDePontuacao(Base):
    __tablename__ = 'registros_de_pontuacao'

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    tarefa_id = Column(Integer, ForeignKey('tarefas.id'), nullable=False)
    data_execucao = Column(Date, nullable=False)
    pontos = Column(Float, nullable=False)
    data_expiracao = Column(Date, nullable=False)
    usado_para_meta = Column(Boolean, default=False)
    quantidade = Column(Integer, default=1)
    numero_processo = Column(String, nullable=True)

    usuario = relationship('Usuario', back_populates='registros')
    tarefa = relationship('Tarefa', back_populates='registros')
    metas = relationship("MetaMensalRegistro", back_populates="registro")

    def __repr__(self):
        return f"<RegistroDePontuacao(id={self.id}, usuario_id={self.usuario_id}, tarefa_id={self.tarefa_id}, pontos={self.pontos})>"

# ----------------------------
# 🎯 Meta Mensal
# ----------------------------
class MetaMensal(Base):
    __tablename__ = 'metas_mensais'

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    ano_mes = Column(String(7), nullable=False)  # YYYY-MM
    pontos_utilizados = Column(Float, nullable=False)
    status = Column(String, nullable=False, default=StatusMeta.PENDENTE.value)
    data_validacao = Column(Date)
    validador_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)

    usuario = relationship('Usuario', back_populates='metas', foreign_keys=[usuario_id])
    validador = relationship('Usuario', back_populates='metas_validadas', foreign_keys=[validador_id])

    def __repr__(self):
        return f"<MetaMensal(id={self.id}, usuario_id={self.usuario_id}, status='{self.status}', ano_mes='{self.ano_mes}')>"

class MetaMensalRegistro(Base):
    __tablename__ = "meta_mensal_registro"

    id = Column(Integer, primary_key=True)
    meta_id = Column(Integer, ForeignKey("metas_mensais.id"))
    registro_id = Column(Integer, ForeignKey("registros_de_pontuacao.id"))
    quantidade_utilizada = Column(Integer)

    # 🔗 Relacionamento com RegistroDePontuacao
    registro = relationship("RegistroDePontuacao", back_populates="metas")

