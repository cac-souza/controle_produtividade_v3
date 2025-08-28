# controle_produtividade_v3
Versão finalizada em 27/08/2025

# 📊 Painel de Produtividade e Metas

Sistema web desenvolvido para gestão de produtividade fiscal, com foco em controle de tarefas, pontuação individual, validação de metas mensais e geração de relatórios formais. A aplicação é voltada para ambientes organizacionais que exigem rastreabilidade, meritocracia e transparência na avaliação de desempenho.

## 🎯 Objetivo

O projeto tem como finalidade:

- Automatizar o registro de atividades realizadas por fiscais
- Calcular pontuação com base em tabela oficial de tarefas
- Validar metas mensais com controle de duplicidade e expiração
- Gerar relatórios em PDF para prestação de contas
- Organizar usuários por setor, equipe e papel funcional

## 🧱 Funcionalidades

- 🔐 Autenticação com controle de acesso por papel (admin, gestor, fiscal etc.)
- 👥 Cadastro de usuários com vínculo a setor e equipe
- ✅ Registro de tarefas com pontuação, prioridade e status
- 📝 Registro de produtividade com número de processo e data de execução
- 📅 Validação de metas mensais com rastreabilidade
- 📈 Consulta de saldo de pontos e registros expirando
- 📋 Geração de relatórios em PDF por período e fiscal responsável
- 📊 Relatório mensal detalhado com base em tabela oficial de atividades

## 🛠️ Tecnologias Utilizadas

- Python 3
- Streamlit (interface web)
- SQLAlchemy ORM (modelagem de dados)
- Alembic (migrations)
- SQLite (banco de dados local)
- Bcrypt (criptografia de senhas)
- FPDF (geração de relatórios em PDF)
- Dateutil (manipulação de datas)
- Base64 (visualização embutida de PDFs)

## 📁 Estrutura do Projeto

| Arquivo / Módulo             | Descrição                                                                 |
|------------------------------|---------------------------------------------------------------------------|
| `modelos.py`                 | Modelagem das tabelas e relacionamentos com SQLAlchemy                    |
| `cadastro_usuario.py`        | Interface para cadastro de novos usuários                                |
| `cadastrar_produtividade.py` | Registro de produtividade com validação de duplicidade                    |
| `consulta_pontuacao.py`      | Consulta de registros, métricas, confirmação de metas e geração de relatórios |
| `auth.py`                    | Controle de login e verificação de permissões                            |
| `helpers.py`                 | Funções auxiliares para filtragem de usuários visíveis                    |
| `painel.py`                  | Página principal do sistema                                              |
| `controle_produtividade.db`  | Banco de dados local com os registros do sistema                         |

## 🚀 Como Executar

1. Clone o repositório:
   ```bash
   git clone https://github.com/cac-souza/controle_produtividade_v3.git
   cd controle_produtividade_v3
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
3. Execute o painel:
   ```bash
   streamlit run painel.py

## 📄 Relatórios em PDF

- Gerados diretamente na interface Streamlit
- Organizados por período e fiscal responsável
- Incluem registros utilizados, tarefas, pontuação e totais
- Relatório mensal baseado em tabela oficial de atividades
- Visualização embutida e opção de download

## 📌 Status do Projeto

✅ Versão finalizada em 27/08/2025  
🚧 Melhorias futuras podem incluir integração com banco de dados remoto, autenticação via OAuth e exportação em outros formatos.

## 🤝 Contribuições

Este projeto está aberto a sugestões e melhorias. Sinta-se à vontade para abrir issues, enviar pull requests ou entrar em contato para colaboração.

## ✍️ Autor

Desenvolvido por Cléber Américo Castro e Souza  
📧 Contato: cleberacsouza@gmail.com  
🔗 GitHub: [github.com/cac-souza](https://github.com/cac-souza

---


