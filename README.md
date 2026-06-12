# Gantt KPI — Gestão de Projetos com Gráfico de Gantt

Aplicação web local para gestão de tarefas das áreas de **PCP e Suprimentos**, com gráfico de Gantt dinâmico gerado automaticamente a partir das tarefas cadastradas.

![Gantt KPI](static/Gantt%20Analyst%20Copilot.png)

## Funcionalidades

- **CRUD de tarefas**: nome, responsável, datas de início/fim e status
- **Gráfico de Gantt dinâmico** (Plotly), estilizado para manter a aparência de relatórios Excel
- **Persistência em SQLite** — o banco é criado automaticamente na primeira execução
- **100% local e em PT-BR**: roda no navegador, sem serviços externos

## Stack

Python 3 · Flask · Flask-SQLAlchemy · SQLite · Pandas · Plotly

## Como executar

Pré-requisito: Python 3.8+

```bash
python -m venv venv
venv\Scripts\activate     # Windows · use: source venv/bin/activate no Linux/macOS
pip install -r requirements.txt
python app.py
```

Acesse `http://localhost:5000`. O arquivo `tasks.db` é criado sozinho na primeira execução.

## Estrutura

```
app.py            # Rotas, modelo de dados e geração do gráfico
templates/        # base.html, index.html (lista + Gantt), edit.html
static/           # Estilos e imagens
requirements.txt  # Dependências
```

## Roadmap

- Importação de tarefas via Excel (carteira de produção real)
- Filtros por responsável e status
- Exportação do gráfico como imagem

## Licença

MIT
