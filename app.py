from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from flask import g
import sqlite3
import atexit
from werkzeug.security import check_password_hash, generate_password_hash 

# Configuração do banco de dados (mantenha apenas uma versão)
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('db/os.db')
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA busy_timeout=5000")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

app = Flask(__name__)
app.secret_key = 'pokemar16'

# Rota inicial
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        conn = get_db()
        cursor = conn.cursor()
        
        # Busca apenas o usuário (não compare a senha diretamente)
        cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['senha'], senha):  # Verifica o hash
            session['usuario'] = user['usuario']
            session['tipo'] = user['tipo']
            session['user_id'] = user['id']  # Armazena o ID do usuário na sessão

            if user['tipo'] == 'solicitante':
                return redirect(url_for('abrir_os'))
            elif user['tipo'] == 'manutencao':
                return redirect(url_for('manutencao_dashboard'))
            elif user['tipo'] == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Usuário ou senha inválidos.')

    return render_template('login.html')

# Rota logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/manutencao/os/<int:id>')
def detalhe_os(id):
    if session.get('tipo') != 'manutencao':
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Busca a OS principal com informações do solicitante e técnico
        cursor.execute("""
            SELECT os.*, 
                   s.nome as solicitante_nome,
                   s.email as solicitante_email,
                   t.nome as tecnico_nome,
                   t.email as tecnico_email
            FROM ordens_servico os
            LEFT JOIN usuarios s ON os.solicitante_id = s.id
            LEFT JOIN usuarios t ON os.tecnico_id = t.id
            WHERE os.id = ?
        """, (id,))
        os_data = cursor.fetchone()
        
        if not os_data:
            flash('Ordem de Serviço não encontrada.', 'danger')
            return redirect(url_for('manutencao_dashboard'))
        
        # Prepara os dados para o template
        os_dict = {
            'id': os_data['id'],
            'equipamento': os_data['equipamento'],
            'problema': os_data['problema'],
            'prioridade': os_data['prioridade'],
            'status': os_data['status'],
            'data': os_data['data'],
            'solucao': os_data['solucao'],
            'tempo_reparo': os_data['tempo_reparo'],
            'fim': os_data['fim']
        }
        
        # Cria objetos para solicitante e técnico
        solicitante = {
            'nome': os_data['solicitante_nome'],
            'email': os_data['solicitante_email']
        }
        
        tecnico = {
            'nome': os_data['tecnico_nome'],
            'email': os_data['tecnico_email']
        } if os_data['tecnico_nome'] else None
        
        # Busca histórico de alterações (se aplicável)
        cursor.execute("""
            SELECT h.*, u.nome as usuario_nome
            FROM historico_os h
            JOIN usuarios u ON h.usuario_id = u.id
            WHERE h.os_id = ?
            ORDER BY h.data_alteracao DESC
        """, (id,))
        historico = cursor.fetchall()
        
        return render_template(
            'manutencao/detalhe_os.html',
            os=os_dict,
            solicitante=solicitante,
            tecnico=tecnico,
            historico=historico
        )
        
    except Exception as e:
        flash(f'Erro ao acessar OS: {str(e)}', 'danger')
        app.logger.error(f"Erro ao acessar OS {id}: {str(e)}")
        return redirect(url_for('manutencao_dashboard'))
        
    finally:
        if conn:
            conn.close()

@app.route('/manutencao/agendar/<int:id>', methods=['GET', 'POST'])
def agendar_os(id):
    if session.get('tipo') != 'manutencao':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        data_agendamento = request.form['data_agendamento']
        horario_agendamento = request.form['horario_agendamento']
        
        try:
            cursor.execute("""
                UPDATE ordens_servico 
                SET data_agendamento = ?, 
                    horario_agendamento = ?,
                    status = 'Agendada',
                    tecnico_id = ?
                WHERE id = ?
            """, (data_agendamento, horario_agendamento, session.get('user_id'), id))
            
            # Registrar no histórico
            cursor.execute("""
                INSERT INTO historico_os 
                (os_id, usuario_id, acao, observacao)
                VALUES (?, ?, ?, ?)
            """, (id, session.get('user_id'), 'OS Agendada', 
                 f"Agendado para {data_agendamento} {horario_agendamento}"))
            
            conn.commit()
            flash('OS agendada com sucesso!', 'success')
            return redirect(url_for('manutencao_dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'Erro ao agendar: {str(e)}', 'danger')
    
    # Busca os dados da OS
    cursor.execute("SELECT * FROM ordens_servico WHERE id = ?", (id,))
    os_data = cursor.fetchone()
    
    conn.close()
    
    return render_template('manutencao/agendar_os.html', os=os_data)

@app.route('/solicitante/minhas_os')
def minhas_os():
    if session.get('tipo') != 'solicitante':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    
    # Busca o ID do solicitante
    cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (session['usuario'],))
    user = cursor.fetchone()
    
    # Busca todas as OSs do solicitante que não estão concluídas
    cursor.execute("""
        SELECT os.*, u.nome as tecnico_nome
        FROM ordens_servico os
        LEFT JOIN usuarios u ON os.tecnico_id = u.id
        WHERE os.solicitante_id = ? AND os.status != 'Concluída'
        ORDER BY os.data DESC
    """, (user['id'],))
    os_abertas = cursor.fetchall()
    
    conn.close()

    return render_template('solicitante/minhas_os.html', os_abertas=os_abertas)

# --- SOLICITANTE ---
@app.route('/solicitante/abrir', methods=['GET', 'POST'])
def abrir_os():
    if session.get('tipo') != 'solicitante':
        return redirect(url_for('login'))

    if request.method == 'POST':
        equipamento = request.form.get('equipamento', '').strip()
        problema = request.form.get('problema', '').strip()
        prioridade = request.form.get('prioridade', 'normal')
        data_agendamento = request.form.get('data_agendamento') if prioridade == 'normal' else None
        horario_agendamento = request.form.get('horario_agendamento') if prioridade == 'normal' else None
        
        if not equipamento or not problema:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return render_template('solicitante/abrir_os.html')
        
        data_abertura = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (session['usuario'],))
            user = cursor.fetchone()
            
            cursor.execute("""
                INSERT INTO ordens_servico 
                (data, equipamento, problema, prioridade, status, solicitante_id, data_agendamento, horario_agendamento) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (data_abertura, equipamento, problema, prioridade, 'Aberta', user['id'], data_agendamento, horario_agendamento))
            
            conn.commit()
            flash('Ordem de serviço enviada com sucesso.', 'success')
            return redirect(url_for('abrir_os'))
            
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'Erro ao salvar OS: {str(e)}', 'danger')
        finally:
            conn.close()
    
    return render_template('solicitante/abrir_os.html')

# --- MANUTENÇÃO ---
@app.route('/manutencao')
def manutencao_dashboard():
    if session.get('tipo') != 'manutencao':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ordens_servico WHERE status != 'Concluída'")
    os_abertas = cursor.fetchall()
    conn.close()

    return render_template('manutencao/listar_os.html', os_abertas=os_abertas)

@app.route('/manutencao/concluir/<int:id>', methods=['POST'])
def concluir_os(id):
    if session.get('tipo') != 'manutencao':
        return redirect(url_for('login'))

    solucao = request.form['solucao']
    fim = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM ordens_servico WHERE id = ?", (id,))
    inicio = datetime.strptime(cursor.fetchone()['data'], '%Y-%m-%d %H:%M:%S')
    tempo_total = (datetime.strptime(fim, '%Y-%m-%d %H:%M:%S') - inicio).total_seconds() / 60

    cursor.execute("""
        UPDATE ordens_servico
        SET solucao = ?, status = 'Concluída', tempo_reparo = ?, fim = ?
        WHERE id = ?
    """, (solucao, tempo_total, fim, id))
    conn.commit()
    conn.close()
    flash('OS concluída.')
    return redirect(url_for('manutencao_dashboard'))

# --- ADMIN ---
@app.route('/admin')
def admin_dashboard():
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    
    # Busca estatísticas
    cursor.execute("""
        SELECT 
            COUNT(*) AS total,
            AVG(tempo_reparo) AS media,
            SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END) AS concluidas,
            SUM(CASE WHEN status = 'Aberta' THEN 1 ELSE 0 END) AS abertas,
            SUM(CASE WHEN status = 'Em andamento' THEN 1 ELSE 0 END) AS em_andamento
        FROM ordens_servico
    """)
    stats = cursor.fetchone()
    
    # Busca todas as OS, incluindo as concluídas, com informações do solicitante
    cursor.execute("""
        SELECT os.*, u.nome as solicitante_nome
        FROM ordens_servico os
        JOIN usuarios u ON os.solicitante_id = u.id
        ORDER BY os.data DESC
        LIMIT 50
    """)
    todas_os = cursor.fetchall()
    
    conn.close()

    return render_template(
        'administrador/dashboard.html',
        stats=stats,
        todas_os=todas_os
    )


@app.route('/admin/os/<int:id>')
def detalhe_os_admin(id):
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Busca a OS com informações completas
        cursor.execute("""
            SELECT os.*, 
                   s.nome as solicitante_nome,
                   s.email as solicitante_email,
                   t.nome as tecnico_nome,
                   t.email as tecnico_email
            FROM ordens_servico os
            LEFT JOIN usuarios s ON os.solicitante_id = s.id
            LEFT JOIN usuarios t ON os.tecnico_id = t.id
            WHERE os.id = ?
        """, (id,))
        os_data = cursor.fetchone()
        
        if not os_data:
            flash('Ordem de Serviço não encontrada.', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        # Converter Row para dicionário e tratar campos opcionais
        os_dict = {
            'id': os_data['id'],
            'equipamento': os_data['equipamento'],
            'problema': os_data['problema'],
            'prioridade': os_data['prioridade'],
            'status': os_data['status'],
            'data': os_data['data'],
            'solucao': os_data['solucao'] if 'solucao' in os_data and os_data['solucao'] else None,
            'tempo_reparo': os_data['tempo_reparo'] if 'tempo_reparo' in os_data else None,
            'inicio': os_data['inicio'] if 'inicio' in os_data else None,
            'fim': os_data['fim'] if 'fim' in os_data else None,
            'local': os_data['local'] if 'local' in os_data else None,
            'setor': os_data['setor'] if 'setor' in os_data else None
        }
        
        solicitante_info = {
            'nome': os_data['solicitante_nome'],
            'email': os_data['solicitante_email']
        }
        
        tecnico_info = {
            'nome': os_data['tecnico_nome'],
            'email': os_data['tecnico_email']
        } if os_data['tecnico_nome'] else None
        
        # Busca histórico
        cursor.execute("""
            SELECT h.*, u.nome as usuario_nome
            FROM historico_os h
            JOIN usuarios u ON h.usuario_id = u.id
            WHERE h.os_id = ?
            ORDER BY h.data_alteracao DESC
        """, (id,))
        historico = cursor.fetchall()
        
        return render_template(
            'administrador/detalhes_os.html',
            os=os_dict,
            solicitante=solicitante_info,
            tecnico=tecnico_info,
            historico=historico
        )
        
    except Exception as e:
        flash(f'Erro ao acessar OS: {str(e)}', 'danger')
        app.logger.error(f"Erro ao acessar OS {id}: {str(e)}")
        return redirect(url_for('admin_dashboard'))
        
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

# No final do arquivo, antes do app.run()
app.teardown_appcontext(close_db)