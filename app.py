from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from flask import g
import sqlite3
import atexit
from werkzeug.security import check_password_hash, generate_password_hash 
from functools import wraps


def manutencao_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('tipo') != 'manutencao':
            flash('Acesso não autorizado', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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


# --- SOLICITANTE ---
@app.route('/solicitante/abrir', methods=['GET', 'POST']) # Considere renomear a rota para algo mais genérico como /os/abrir se preferir
def abrir_os():
    if session.get('tipo') not in ['solicitante', 'admin']: # MODIFICADO AQUI
        flash('Acesso não autorizado para esta funcionalidade.', 'danger')
        return redirect(url_for('login')) # Ou redirecionar para o dashboard apropriado

    if request.method == 'POST':
        equipamento = request.form.get('equipamento', '').strip()
        problema = request.form.get('problema', '').strip()
        prioridade = request.form.get('prioridade', 'normal')
        data_agendamento = request.form.get('data_agendamento') if prioridade == 'normal' else None
        horario_agendamento = request.form.get('horario_agendamento') if prioridade == 'normal' else None
        
        if not equipamento or not problema:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            # Se o admin estiver abrindo, talvez ele deva ser redirecionado para a mesma página de abrir_os
            # e não para a do solicitante especificamente, caso os templates sejam diferentes.
            # Como o template é o mesmo (solicitante/abrir_os.html), isso deve funcionar.
            return render_template('solicitante/abrir_os.html') 
        
        data_abertura = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # O user_id da sessão será usado como solicitante_id,
            # o que é correto, pois o admin é o solicitante neste caso.
            cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (session['usuario'],))
            user = cursor.fetchone()
            
            cursor.execute("""
                INSERT INTO ordens_servico 
                (data, equipamento, problema, prioridade, status, solicitante_id, data_agendamento, horario_agendamento) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (data_abertura, equipamento, problema, prioridade, 'Aberta', user['id'], data_agendamento, horario_agendamento))
            
            conn.commit()
            flash('Ordem de serviço enviada com sucesso.', 'success')
            # Após o admin abrir uma OS, ele pode ser redirecionado para o dashboard dele ou para a página de abrir_os novamente
            if session.get('tipo') == 'admin':
                return redirect(url_for('admin_dashboard')) # Ou para 'abrir_os' se quiser abrir outra
            else:
                return redirect(url_for('abrir_os'))
            
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'Erro ao salvar OS: {str(e)}', 'danger')
        finally:
            conn.close()
    
    # O mesmo template 'solicitante/abrir_os.html' pode ser usado por ambos
    return render_template('solicitante/abrir_os.html')

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

# --- MANUTENÇÃO ---
@app.route('/manutencao')
@manutencao_required
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
    tecnicos_participantes = request.form.getlist('tecnicos_participantes')
    fim = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    try:
        cursor = conn.cursor()
        
        # Calcula tempo de reparo
        cursor.execute("SELECT data, inicio FROM ordens_servico WHERE id = ?", (id,))
        os_data = cursor.fetchone()
        
        inicio = os_data['inicio'] if os_data['inicio'] else os_data['data']
        inicio_dt = datetime.strptime(inicio, '%Y-%m-%d %H:%M:%S')
        fim_dt = datetime.strptime(fim, '%Y-%m-%d %H:%M:%S')
        tempo_total = (fim_dt - inicio_dt).total_seconds() / 60  # em minutos

        # Atualiza a OS
        cursor.execute("""
            UPDATE ordens_servico
            SET solucao = ?, 
                status = 'Concluída', 
                tempo_reparo = ?, 
                fim = ?,
                inicio = ?
            WHERE id = ?
        """, (solucao, tempo_total, fim, inicio, id))
        
        # Adiciona técnicos participantes
        for tecnico_id in tecnicos_participantes:
            cursor.execute("""
                INSERT OR IGNORE INTO participantes_os (os_id, tecnico_id)
                VALUES (?, ?)
            """, (id, tecnico_id))
        
        # Registra no histórico
        cursor.execute("""
            INSERT INTO historico_os 
            (os_id, usuario_id, acao)
            VALUES (?, ?, ?)
        """, (id, session.get('user_id'), 'OS Concluída'))
        
        conn.commit()
        flash('OS concluída com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao concluir OS: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('manutencao_dashboard'))

@app.route('/manutencao/iniciar/<int:id>')
def iniciar_os(id):
    if session.get('tipo') != 'manutencao':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Verifica se está agendada
        cursor.execute("SELECT status FROM ordens_servico WHERE id = ?", (id,))
        os_status = cursor.fetchone()['status']
        
        if os_status != 'Agendada':
            flash('Só é possível iniciar OSs agendadas', 'warning')
            return redirect(url_for('manutencao_dashboard'))
        
        # Atualiza status
        cursor.execute("""
            UPDATE ordens_servico 
            SET status = 'Em andamento',
                inicio = datetime('now')
            WHERE id = ?
        """, (id,))
        
        # Registra no histórico
        cursor.execute("""
            INSERT INTO historico_os 
            (os_id, usuario_id, acao)
            VALUES (?, ?, ?)
        """, (id, session.get('user_id'), 'Reparo iniciado'))
        
        conn.commit()
        flash('Reparo iniciado com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao iniciar reparo: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('manutencao_dashboard'))

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
        tecnicos_participantes = request.form.getlist('tecnicos_participantes')
        
        try:
            # Atualiza a OS com agendamento
            cursor.execute("""
                UPDATE ordens_servico 
                SET data_agendamento = ?, 
                    horario_agendamento = ?,
                    status = 'Agendada',
                    tecnico_id = ?
                WHERE id = ?
            """, (data_agendamento, horario_agendamento, session.get('user_id'), id))
            
            # Adiciona técnicos participantes
            for tecnico_id in tecnicos_participantes:
                cursor.execute("""
                    INSERT INTO participantes_os (os_id, tecnico_id)
                    VALUES (?, ?)
                """, (id, tecnico_id))
            
            # Registra no histórico
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
    
    # Busca dados da OS
    cursor.execute("SELECT * FROM ordens_servico WHERE id = ?", (id,))
    os_data = cursor.fetchone()
    
    # Busca lista de técnicos disponíveis (exceto o próprio usuário)
    cursor.execute("""
        SELECT id, nome FROM usuarios 
        WHERE tipo = 'manutencao' AND id != ?
        ORDER BY nome
    """, (session.get('user_id'),))
    tecnicos = cursor.fetchall()
    
    conn.close()
    
    return render_template('manutencao/agendar_os.html', 
                         os=os_data, 
                         tecnicos=tecnicos)

# --- ADMIN ---
@app.route('/admin')
def admin_dashboard():
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    
    # Busca estatísticas com tratamento para valores nulos
    cursor.execute("""
        SELECT 
            COUNT(*) AS total,
            AVG(CASE WHEN tempo_reparo IS NOT NULL THEN tempo_reparo ELSE 0 END) AS media,
            SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END) AS concluidas,
            SUM(CASE WHEN status = 'Aberta' THEN 1 ELSE 0 END) AS abertas,
            SUM(CASE WHEN status = 'Em andamento' THEN 1 ELSE 0 END) AS em_andamento,
            SUM(CASE WHEN status = 'Agendada' THEN 1 ELSE 0 END) AS agendadas
        FROM ordens_servico
    """)
    stats = cursor.fetchone()
    
    # Busca todas as OSs para exibição
    cursor.execute("""
        SELECT os.*, u.nome as solicitante_nome
        FROM ordens_servico os
        JOIN usuarios u ON os.solicitante_id = u.id
        ORDER BY os.data DESC
        LIMIT 50
    """)
    todas_os = cursor.fetchall()
    
    conn.close()

    # Garante que a média será um número válido
    stats_dict = dict(stats)
    stats_dict['media'] = stats_dict['media'] if stats_dict['media'] is not None else 0

    return render_template(
        'administrador/dashboard.html',
        stats=stats_dict,
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
        
        # Busca participantes da OS
        participantes = []
        cursor.execute("""
            SELECT u.id, u.nome, u.email
            FROM participantes_os p
            JOIN usuarios u ON p.tecnico_id = u.id
            WHERE p.os_id = ?
        """, (id,))
        participantes = [dict(part) for part in cursor.fetchall()]  # Convertendo para dicionário

        # Adiciona o técnico principal se existir
        if os_data['tecnico_id']:
            cursor.execute("SELECT id, nome, email FROM usuarios WHERE id = ?", (os_data['tecnico_id'],))
            tecnico_principal = cursor.fetchone()
            if tecnico_principal:
                participantes.append({
                    'id': tecnico_principal['id'],
                    'nome': tecnico_principal['nome'],
                    'email': tecnico_principal['email'],
                    'funcao': 'Responsável'
                })

        # Convertendo os_data para dicionário
        os_dict = {
            'id': os_data['id'],
            'equipamento': os_data['equipamento'],
            'problema': os_data['problema'],
            'prioridade': os_data['prioridade'],
            'status': os_data['status'],
            'data': os_data['data'],
            'solucao': os_data['solucao'],
            'tempo_reparo': os_data['tempo_reparo'] if 'tempo_reparo' in os_data and os_data['tempo_reparo'] is not None else None,
            'inicio': os_data['inicio'] if 'inicio' in os_data and os_data['inicio'] is not None else None,
            'fim': os_data['fim'] if 'fim' in os_data and os_data['fim'] is not None else None,
            'local': os_data['local'] if 'local' in os_data and os_data['local'] is not None else None,
            'setor': os_data['setor'] if 'setor' in os_data and os_data['setor'] is not None else None
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
        historico = []
        cursor.execute("""
            SELECT h.*, u.nome as usuario_nome
            FROM historico_os h
            JOIN usuarios u ON h.usuario_id = u.id
            WHERE h.os_id = ?
            ORDER BY h.data_alteracao DESC
        """, (id,))
        historico = [dict(h) for h in cursor.fetchall()]  # Convertendo para dicionário
        
        return render_template(
            'administrador/detalhes_os.html',
            os=os_dict,
            solicitante=solicitante_info,
            tecnico=tecnico_info,
            participantes=participantes,
            historico=historico
        )
        
    except Exception as e:
        flash(f'Erro ao acessar OS: {str(e)}', 'danger')
        app.logger.error(f"Erro ao acessar OS {id}: {str(e)}")
        return redirect(url_for('admin_dashboard'))
        
    finally:
        conn.close()

# --- ADMIN - Gerenciamento de Usuários ---
@app.route('/admin/usuarios')
def listar_usuarios():
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios ORDER BY nome")
    usuarios = cursor.fetchall()
    conn.close()

    return render_template('administrador/listar_usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/novo', methods=['GET', 'POST'])
def novo_usuario():
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        tipo = request.form['tipo']
        nome = request.form['nome']
        email = request.form['email']
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usuarios (usuario, senha, tipo, nome, email)
                VALUES (?, ?, ?, ?, ?)
            ''', (usuario, generate_password_hash(senha), tipo, nome, email))
            conn.commit()
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('listar_usuarios'))
        except sqlite3.IntegrityError:
            flash('Usuário ou email já existente!', 'danger')
        except Exception as e:
            flash(f'Erro ao criar usuário: {str(e)}', 'danger')
        finally:
            conn.close()

    return render_template('administrador/novo_usuario.html')

@app.route('/admin/usuarios/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        usuario = request.form['usuario']
        tipo = request.form['tipo']
        nome = request.form['nome']
        email = request.form['email']
        ativo = request.form.get('ativo', 0)
        
        try:
            # Atualiza sem senha (senha é alterada separadamente)
            cursor.execute('''
                UPDATE usuarios 
                SET usuario = ?, tipo = ?, nome = ?, email = ?, ativo = ?
                WHERE id = ?
            ''', (usuario, tipo, nome, email, 1 if ativo == 'on' else 0, id))
            conn.commit()
            flash('Usuário atualizado com sucesso!', 'success')
        except sqlite3.IntegrityError:
            flash('Usuário ou email já existente!', 'danger')
        except Exception as e:
            flash(f'Erro ao atualizar usuário: {str(e)}', 'danger')
        finally:
            conn.close()
            return redirect(url_for('listar_usuarios'))

    # GET - Carrega dados do usuário
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (id,))
    usuario = cursor.fetchone()
    conn.close()

    if not usuario:
        flash('Usuário não encontrado!', 'danger')
        return redirect(url_for('listar_usuarios'))

    return render_template('administrador/editar_usuario.html', usuario=usuario)

@app.route('/admin/usuarios/alterar_senha/<int:id>', methods=['POST'])
def alterar_senha_usuario(id):
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    nova_senha = request.form['nova_senha']
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE usuarios 
            SET senha = ?
            WHERE id = ?
        ''', (generate_password_hash(nova_senha), id))
        conn.commit()
        flash('Senha alterada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao alterar senha: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('editar_usuario', id=id))

@app.route('/admin/usuarios/remover/<int:id>')
def remover_usuario(id):
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    # Não permite remover o próprio admin
    if id == session.get('user_id'):
        flash('Você não pode remover a si mesmo!', 'danger')
        return redirect(url_for('listar_usuarios'))

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (id,))
        conn.commit()
        flash('Usuário removido com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao remover usuário: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('listar_usuarios'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

# No final do arquivo, antes do app.run()
app.teardown_appcontext(close_db)