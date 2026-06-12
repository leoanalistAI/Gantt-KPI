import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import plotly.express as px
import plotly.io as pio

# --- Configuração Inicial ---
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'tasks.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Modelo do Banco de Dados ---
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.String(10), nullable=False)
    end_date = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<Task {self.name}>'



# --- Rotas da Aplicação ---
@app.route('/')
def index():
    tasks = Task.query.order_by(Task.start_date).all()
    gantt_chart_html = create_gantt_chart(tasks)
    return render_template('index.html', tasks=tasks, gantt_chart_html=gantt_chart_html)

@app.route('/add', methods=['POST'])
def add_task():
    new_task = Task(
        name=request.form['name'],
        owner=request.form['owner'],
        start_date=request.form['start_date'],
        end_date=request.form['end_date'],
        status=request.form['status']
    )
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_task(id):
    task_to_delete = Task.query.get_or_404(id)
    db.session.delete(task_to_delete)
    db.session.commit()
    return redirect(url_for('index'))

# --- Lógica para Geração do Gráfico ---
def create_gantt_chart(tasks):
    if not tasks:
        return "<p>Nenhuma tarefa para exibir. Adicione uma tarefa para gerar o gráfico.</p>"

    color_map = {
        'Concluído': '#4CAF50',
        'Em Andamento': '#2196F3',
        'Atrasado': '#F44336',
        'Não Iniciado': '#9E9E9E'
    }

    df = pd.DataFrame([{
        'Tarefa': task.name,
        'Start': task.start_date,
        'Finish': task.end_date,
        'Status': task.status,
        'Responsável': task.owner
    } for task in tasks])

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Tarefa",
        color="Status",
        color_discrete_map=color_map,
        hover_name="Responsável",
        # LINHA ALTERADA: Adicionamos as traduções para 'Start', 'Finish' e 'Status'
        labels={
            'Tarefa': 'Tarefas',
            'Start': 'Início',
            'Finish': 'Término',
            'Status': 'Status'
        }
    )

    fig.update_layout(
        title_text='Cronograma do Projeto (Gráfico de Gantt)',
        font=dict(
            family="Calibri, sans-serif",
            size=12,
            color="#000000"
        ),
        plot_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgrey',
            gridwidth=1,
            tickformat="%d/%m/%Y"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgrey',
            gridwidth=1
        ),
        bargap=0.5,
        legend_title_text='Status'
    )

    fig.update_yaxes(autorange="reversed")

    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

# Adicione este novo bloco de código no seu app.py

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update_task(id):
    task = Task.query.get_or_404(id)

    if request.method == 'POST':
        task.name = request.form['name']
        task.owner = request.form['owner']
        task.start_date = request.form['start_date']
        task.end_date = request.form['end_date']
        task.status = request.form['status']
        
        try:
            db.session.commit()
            return redirect(url_for('index'))
        except:
            return 'Houve um problema ao atualizar a tarefa.'
    else:
        return render_template('edit.html', task=task)


if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Cria o arquivo do banco de dados se ele não existir
    app.run(debug=True)