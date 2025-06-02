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
    if 'usuario' in session:
        if session['tipo'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['tipo'] == 'manutencao':
            return redirect(url_for('manutencao_dashboard'))
        else: # solicitante
            return redirect(url_for('abrir_os')) # ou minhas_os
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
                return redirect(url_for('minhas_os')) # MODIFICADO AQUI
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
@app.route('/solicitante/abrir', methods=['GET', 'POST']) # Ou a URL que você estiver usando, ex: /os/abrir
def abrir_os():
    # Verificação de permissão (mantida da sua versão e sugestões anteriores)
    if session.get('tipo') not in ['solicitante', 'admin']:
        flash('Acesso não autorizado para esta funcionalidade.', 'danger')
        return redirect(url_for('login'))

    # Obter a conexão gerenciada pelo Flask para esta requisição
    conn = get_db()
    cursor = conn.cursor()

    # Buscar locais ativos para o formulário (executado em GET e antes do POST)
    cursor.execute("SELECT id, nome FROM locais WHERE ativo = 1 ORDER BY nome")
    locais_ativos = cursor.fetchall()

    if request.method == 'POST':
        equipamento = request.form.get('equipamento', '').strip()
        problema = request.form.get('problema', '').strip()
        prioridade = request.form.get('prioridade', 'normal')
        local_selecionado = request.form.get('local') # Nome do local
        setor = request.form.get('setor', '').strip() # Campo setor

        data_agendamento = request.form.get('data_agendamento') if prioridade == 'normal' else None
        horario_agendamento = request.form.get('horario_agendamento') if prioridade == 'normal' else None
        
        if not equipamento or not problema or not local_selecionado:
            flash('Preencha todos os campos obrigatórios (Equipamento, Problema e Local).', 'danger')
            # locais_ativos já foi buscado, pode renderizar o template diretamente
            # A conexão será fechada automaticamente pelo teardown_appcontext
            return render_template('solicitante/abrir_os.html', locais=locais_ativos)
        
        data_abertura = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # O cursor já está pronto para uso
            cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (session['usuario'],))
            user = cursor.fetchone()
            
            if not user: # Adicionar verificação caso o usuário não seja encontrado na sessão
                flash('Erro de sessão do usuário. Por favor, faça login novamente.', 'danger')
                return redirect(url_for('login'))

            # Salvar o nome do local diretamente na coluna 'local' (que é TEXT)
            cursor.execute("""
                INSERT INTO ordens_servico 
                (data, equipamento, problema, prioridade, status, solicitante_id, 
                 local, setor, data_agendamento, horario_agendamento) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data_abertura, equipamento, problema, prioridade, 'Aberta', user['id'], 
                  local_selecionado, setor, data_agendamento, horario_agendamento))
            
            conn.commit() # Commit na conexão gerenciada
            flash('Ordem de serviço enviada com sucesso!', 'success')
            
            # Redirecionamento após sucesso
            if session.get('tipo') == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                # Para solicitantes, talvez redirecionar para 'minhas_os' ou uma página de sucesso específica
                # em vez de voltar para 'abrir_os' e potencialmente reenviar o formulário com F5.
                return redirect(url_for('minhas_os')) # Sugestão: redirecionar para minhas_os
            
        except sqlite3.Error as e:
            conn.rollback() # Rollback na conexão gerenciada
            flash(f'Erro ao salvar OS: {str(e)}', 'danger')
        # A conexão será fechada automaticamente pelo teardown_appcontext
    
    # Para requisições GET, locais_ativos já foi buscado
    # A conexão será fechada automaticamente pelo teardown_appcontext
    return render_template('solicitante/abrir_os.html', locais=locais_ativos)

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
            'local': os_data['local'] if 'local' in os_data.keys() and os_data['local'] is not None else None,
            'setor': os_data['setor'] if 'setor' in os_data.keys() and os_data['setor'] is not None else None
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

# --- ADMIN - Configurações ---
@app.route('/admin/configuracoes')
def admin_configuracoes():
    if session.get('tipo') != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))
    return render_template('administrador/configuracoes.html')

# --- ADMIN - Gerenciamento de Locais ---
@app.route('/admin/locais')
def listar_locais():
    if session.get('tipo') != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locais ORDER BY nome")
    locais = cursor.fetchall()
    conn.close()
    return render_template('administrador/listar_locais.html', locais=locais)

@app.route('/admin/locais/adicionar', methods=['GET', 'POST'])
def adicionar_local():
    if session.get('tipo') != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = 1 if request.form.get('ativo') == '1' else 0

        if not nome:
            flash('O nome do local é obrigatório.', 'danger')
            return render_template('administrador/form_local.html', local=None) # Retorna para o form com dados preenchidos

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO locais (nome, descricao, ativo) VALUES (?, ?, ?)",
                (nome, descricao, ativo)
            )
            conn.commit()
            flash('Local adicionado com sucesso!', 'success')
            return redirect(url_for('listar_locais'))
        except sqlite3.IntegrityError:
            conn.rollback()
            flash('Já existe um local com este nome.', 'danger')
        except Exception as e:
            conn.rollback()
            flash(f'Erro ao adicionar local: {str(e)}', 'danger')
        finally:
            if conn:
                conn.close()
        # Em caso de erro, recarrega o formulário com os dados inseridos
        return render_template('administrador/form_local.html', local={'nome': nome, 'descricao': descricao, 'ativo': ativo})


    return render_template('administrador/form_local.html', local=None) # Para GET request

@app.route('/admin/locais/editar/<int:id>', methods=['GET', 'POST'])
def editar_local(id):
    if session.get('tipo') != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))

    conn = get_db() # Mova a obtenção da conexão para o início
    cursor = conn.cursor()

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = 1 if request.form.get('ativo') == '1' else 0

        if not nome:
            flash('O nome do local é obrigatório.', 'danger')
            # Para manter os dados no formulário em caso de erro no POST
            cursor.execute("SELECT * FROM locais WHERE id = ?", (id,))
            local_data = cursor.fetchone()
            conn.close()
            if not local_data:
                flash('Local não encontrado.', 'danger')
                return redirect(url_for('listar_locais'))
            # Atualiza o dicionário com os dados do formulário para repopular
            local_dict_for_template = dict(local_data)
            local_dict_for_template['nome'] = nome
            local_dict_for_template['descricao'] = descricao
            local_dict_for_template['ativo'] = ativo
            return render_template('administrador/form_local.html', local=local_dict_for_template)


        try:
            # Verifica se o novo nome já existe para outro ID
            cursor.execute("SELECT id FROM locais WHERE nome = ? AND id != ?", (nome, id))
            outro_local_com_mesmo_nome = cursor.fetchone()
            if outro_local_com_mesmo_nome:
                flash('Já existe outro local com este nome.', 'danger')
            else:
                cursor.execute(
                    "UPDATE locais SET nome = ?, descricao = ?, ativo = ? WHERE id = ?",
                    (nome, descricao, ativo, id)
                )
                conn.commit()
                flash('Local atualizado com sucesso!', 'success')
                conn.close() # Fechar conexão aqui após o commit bem-sucedido
                return redirect(url_for('listar_locais'))
        except sqlite3.Error as e: # Usar sqlite3.Error para ser mais específico
            conn.rollback()
            flash(f'Erro ao atualizar local: {str(e)}', 'danger')
        # Não feche a conexão aqui se houve erro e você vai renderizar o template novamente

    # Para GET request ou se houve erro no POST e precisa recarregar com os dados do BD
    cursor.execute("SELECT * FROM locais WHERE id = ?", (id,))
    local_data = cursor.fetchone()
    conn.close() # Fechar a conexão após buscar os dados para o GET

    if not local_data:
        flash('Local não encontrado.', 'danger')
        return redirect(url_for('listar_locais'))
    
    return render_template('administrador/form_local.html', local=local_data)


@app.route('/admin/locais/remover/<int:id>')
def remover_local(id):
    if session.get('tipo') != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))

    try:
        conn = get_db()
        cursor = conn.cursor()
        # Opcional: Verificar se o local está em uso antes de remover ou apenas desativar.
        # Por simplicidade, vamos remover.
        cursor.execute("DELETE FROM locais WHERE id = ?", (id,))
        conn.commit()
        flash('Local removido com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao remover local: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('listar_locais'))

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
    # Apenas master-admin e admin podem acessar esta página
    if session.get('tipo') not in ['admin', 'master-admin']:
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login')) # Ou para o dashboard apropriado

    tipos_disponiveis_para_criacao = []
    if session.get('tipo') == 'master-admin':
        tipos_disponiveis_para_criacao = [
            {'value': 'solicitante', 'label': 'Solicitante'},
            {'value': 'manutencao', 'label': 'Técnico de Manutenção'},
            {'value': 'admin', 'label': 'Administrador'}
            # Master-admin não cria outro master-admin por este formulário padrão
        ]
    elif session.get('tipo') == 'admin':
        tipos_disponiveis_para_criacao = [
            {'value': 'solicitante', 'label': 'Solicitante'},
            {'value': 'manutencao', 'label': 'Técnico de Manutenção'}
            # Admin não pode criar outros admins ou master-admins
        ]

    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        senha = request.form.get('senha')
        tipo_novo_usuario = request.form.get('tipo')
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        # Captura a especialidade apenas se o tipo for 'manutencao'
        especialidade = request.form.get('especialidade') if tipo_novo_usuario == 'manutencao' else None

        # Validação básica de campos obrigatórios
        if not all([usuario, senha, tipo_novo_usuario, nome, email]):
            flash('Todos os campos marcados com * são obrigatórios.', 'warning')
            return render_template('administrador/novo_usuario.html', 
                                   tipos_disponiveis=tipos_disponiveis_para_criacao,
                                   submitted_data=request.form) # Para repopular o formulário
        
        # Validação de permissão para o tipo de usuário selecionado
        tipos_valores_permitidos = [t['value'] for t in tipos_disponiveis_para_criacao]
        if tipo_novo_usuario not in tipos_valores_permitidos:
            flash('Você não tem permissão para criar este tipo de usuário.', 'danger')
            return render_template('administrador/novo_usuario.html', 
                                   tipos_disponiveis=tipos_disponiveis_para_criacao,
                                   submitted_data=request.form)

        if tipo_novo_usuario == 'manutencao' and not especialidade:
            flash('A especialidade é obrigatória para usuários do tipo Técnico de Manutenção.', 'warning')
            return render_template('administrador/novo_usuario.html', 
                                   tipos_disponiveis=tipos_disponiveis_para_criacao,
                                   submitted_data=request.form)

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usuarios (usuario, senha, tipo, nome, email, especialidade, ativo)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', (usuario, generate_password_hash(senha), tipo_novo_usuario, nome, email, especialidade))
            conn.commit()
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('listar_usuarios'))
        except sqlite3.IntegrityError:
            # conn.rollback() # get_db() e teardown_appcontext devem lidar com isso, mas não custa.
            flash('Nome de usuário ou email já cadastrado.', 'danger')
        except Exception as e:
            # conn.rollback()
            flash(f'Erro ao criar usuário: {str(e)}', 'danger')
        
        # Se chegou aqui, houve um erro na tentativa de inserção, então repopula o form
        return render_template('administrador/novo_usuario.html', 
                               tipos_disponiveis=tipos_disponiveis_para_criacao,
                               submitted_data=request.form)

    # Método GET
    return render_template('administrador/novo_usuario.html', 
                           tipos_disponiveis=tipos_disponiveis_para_criacao)

@app.route('/admin/usuarios/editar/<int:id_usuario_alvo>', methods=['GET', 'POST'])
def editar_usuario(id_usuario_alvo):
    # Quem está logado
    editor_tipo = session.get('tipo')
    editor_id = session.get('user_id')

    if editor_tipo not in ['admin', 'master-admin']:
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (id_usuario_alvo,))
    usuario_alvo = cursor.fetchone()

    if not usuario_alvo:
        flash('Usuário não encontrado!', 'danger')
        return redirect(url_for('listar_usuarios'))

    # --- Lógica de Permissão para Acessar a Página de Edição (GET) e para Salvar (POST) ---
    pode_editar = False
    tipos_disponiveis_para_atribuicao = []

    if editor_tipo == 'master-admin':
        pode_editar = True
        # Master-admin pode atribuir estes tipos:
        tipos_disponiveis_para_atribuicao = [
            {'value': 'solicitante', 'label': 'Solicitante'},
            {'value': 'manutencao', 'label': 'Técnico de Manutenção'},
            {'value': 'admin', 'label': 'Administrador'}
        ]
        # Master-admin não pode rebaixar outro master-admin ou a si mesmo via este form simples
        if usuario_alvo['tipo'] == 'master-admin':
            tipos_disponiveis_para_atribuicao = [{'value': 'master-admin', 'label': 'Master Administrador'}] # Só pode ser master-admin
            if usuario_alvo['id'] == editor_id and sum(1 for row in cursor.execute("SELECT 1 FROM usuarios WHERE tipo = 'master-admin' AND ativo = 1")) <= 1:
                 # Impede o único master-admin ativo de mudar seu próprio tipo se for o único
                 tipos_disponiveis_para_atribuicao = [{'value': 'master-admin', 'label': 'Master Administrador'}]


    elif editor_tipo == 'admin':
        if usuario_alvo['tipo'] == 'master-admin':
            pode_editar = False # Admin não pode editar master-admin
            flash('Administradores não podem editar usuários Master Administrador.', 'warning')
        elif usuario_alvo['tipo'] == 'admin' and usuario_alvo['id'] != editor_id:
            pode_editar = False # Admin não pode editar outros admins
            flash('Administradores não podem editar outros Administradores.', 'warning')
        elif usuario_alvo['id'] == editor_id: # Admin editando a si mesmo
            pode_editar = True # Pode editar seus próprios dados, exceto o tipo
            tipos_disponiveis_para_atribuicao = [{'value': 'admin', 'label': 'Administrador'}] # Tipo fixo
        else: # Admin editando solicitante ou manutencao
            pode_editar = True
            tipos_disponiveis_para_atribuicao = [
                {'value': 'solicitante', 'label': 'Solicitante'},
                {'value': 'manutencao', 'label': 'Técnico de Manutenção'}
            ]
            # Se o usuário alvo já é admin (e o editor não é o mesmo admin), essa condição não deveria ser alcançada
            # por causa do 'elif' anterior. Mas para garantir:
            if usuario_alvo['tipo'] == 'admin':
                 tipos_disponiveis_para_atribuicao = [{'value': 'admin', 'label': 'Administrador'}]


    if not pode_editar and request.method == 'GET': # Redireciona no GET se não puder editar
         return redirect(url_for('listar_usuarios'))


    if request.method == 'POST':
        if not pode_editar: # Dupla verificação para o POST
            flash('Você não tem permissão para modificar este usuário.', 'danger')
            return redirect(url_for('listar_usuarios'))

        nome_form = request.form.get('nome','').strip()
        usuario_form = request.form.get('usuario','').strip() # Usuário (login)
        email_form = request.form.get('email','').strip()
        tipo_form = request.form.get('tipo')
        ativo_form = 1 if request.form.get('ativo') == 'on' else 0 # Checkbox 'on' ou ausente
        especialidade_form = request.form.get('especialidade') if tipo_form == 'manutencao' else None

        # Validação básica
        if not all([nome_form, usuario_form, email_form, tipo_form]):
            flash('Campos Nome, Usuário, Email e Tipo são obrigatórios.', 'warning')
            # Recarrega com os dados do formulário, não do banco, para o usuário corrigir
            usuario_alvo_temp_form = dict(usuario_alvo)
            usuario_alvo_temp_form.update(request.form.to_dict())
            return render_template('administrador/editar_usuario.html', 
                                   usuario=usuario_alvo_temp_form, 
                                   tipos_disponiveis=tipos_disponiveis_para_atribuicao,
                                   pode_alterar_tipo=(usuario_alvo['tipo'] != 'master-admin' and (editor_tipo == 'master-admin' or usuario_alvo['id'] != editor_id)))


        # Validação do tipo selecionado
        tipos_valores_permitidos = [t['value'] for t in tipos_disponiveis_para_atribuicao]
        if tipo_form not in tipos_valores_permitidos:
            flash('Você não tem permissão para atribuir este tipo de usuário.', 'danger')
            # Recarrega como acima
            usuario_alvo_temp_form = dict(usuario_alvo)
            usuario_alvo_temp_form.update(request.form.to_dict())
            return render_template('administrador/editar_usuario.html', 
                                   usuario=usuario_alvo_temp_form, 
                                   tipos_disponiveis=tipos_disponiveis_para_atribuicao,
                                   pode_alterar_tipo=(usuario_alvo['tipo'] != 'master-admin' and (editor_tipo == 'master-admin' or usuario_alvo['id'] != editor_id)))

        if tipo_form == 'manutencao' and not especialidade_form:
            flash('Especialidade é obrigatória para Técnico de Manutenção.', 'warning')
            # Recarrega como acima
            usuario_alvo_temp_form = dict(usuario_alvo)
            usuario_alvo_temp_form.update(request.form.to_dict())
            return render_template('administrador/editar_usuario.html', 
                                   usuario=usuario_alvo_temp_form, 
                                   tipos_disponiveis=tipos_disponiveis_para_atribuicao,
                                   pode_alterar_tipo=(usuario_alvo['tipo'] != 'master-admin' and (editor_tipo == 'master-admin' or usuario_alvo['id'] != editor_id)))
        
        # Lógica para impedir que o único master-admin ativo se desative ou mude de tipo crítico
        if usuario_alvo['tipo'] == 'master-admin' and usuario_alvo['id'] == editor_id:
            if not ativo_form:
                cursor.execute("SELECT COUNT(*) FROM usuarios WHERE tipo = 'master-admin' AND ativo = 1 AND id != ?", (editor_id,))
                outros_master_admins_ativos = cursor.fetchone()[0]
                if outros_master_admins_ativos == 0:
                    flash('Não é possível desativar o único Master Administrador ativo.', 'danger')
                    ativo_form = 1 # Força de volta para ativo
            if tipo_form != 'master-admin':
                 flash('Master Administradores não podem mudar seu próprio tipo desta forma.', 'danger')
                 tipo_form = 'master-admin' # Força de volta para master-admin


        try:
            cursor.execute('''
                UPDATE usuarios 
                SET nome = ?, usuario = ?, email = ?, tipo = ?, especialidade = ?, ativo = ?
                WHERE id = ?
            ''', (nome_form, usuario_form, email_form, tipo_form, especialidade_form, ativo_form, id_usuario_alvo))
            conn.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('listar_usuarios'))
        except sqlite3.IntegrityError:
            # conn.rollback()
            flash('Nome de usuário ou email já existe para outro usuário.', 'danger')
        except Exception as e:
            # conn.rollback()
            flash(f'Erro ao atualizar usuário: {str(e)}', 'danger')
        
        # Se chegou aqui, houve erro no update, repopula o form
        usuario_alvo_temp_form = dict(usuario_alvo)
        usuario_alvo_temp_form.update(request.form.to_dict()) # Pega os valores atuais do form
        return render_template('administrador/editar_usuario.html', 
                               usuario=usuario_alvo_temp_form, 
                               tipos_disponiveis=tipos_disponiveis_para_atribuicao,
                               pode_alterar_tipo=(usuario_alvo['tipo'] != 'master-admin' and (editor_tipo == 'master-admin' or usuario_alvo['id'] != editor_id)))


    # Método GET (se pode_editar for True)
    return render_template('administrador/editar_usuario.html', 
                           usuario=usuario_alvo, 
                           tipos_disponiveis=tipos_disponiveis_para_atribuicao,
                           pode_alterar_tipo=(usuario_alvo['tipo'] != 'master-admin' and (editor_tipo == 'master-admin' or usuario_alvo['id'] != editor_id)))

@app.route('/admin/usuarios/alterar_senha/<int:id_usuario_alvo>', methods=['POST'])
def alterar_senha_usuario(id_usuario_alvo):
    editor_tipo = session.get('tipo')
    editor_id = session.get('user_id')

    if editor_tipo not in ['admin', 'master-admin']:
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))
    nova_senha = request.form.get('nova_senha')
    if not nova_senha:
        flash('Nova senha não pode ser vazia.', 'warning')
        return redirect(url_for('editar_usuario', id_usuario_alvo=id_usuario_alvo)) 
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE usuarios 
            SET senha = ?
            WHERE id = ?
        ''', (generate_password_hash(nova_senha), id_usuario_alvo))
        conn.commit()
        flash('Senha alterada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao alterar senha: {str(e)}', 'danger')
    
    return redirect(url_for('editar_usuario', id_usuario_alvo=id_usuario_alvo))

@app.route('/admin/usuarios/remover/<int:id_usuario_alvo>')
def remover_usuario(id_usuario_alvo):
    editor_tipo = session.get('tipo')
    editor_id = session.get('user_id')

    if editor_tipo not in ['admin', 'master-admin']:
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))

    if id_usuario_alvo == editor_id:
        flash('Você não pode remover a si mesmo!', 'danger')
        return redirect(url_for('listar_usuarios'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (id_usuario_alvo,))
    usuario_alvo = cursor.fetchone()

    if not usuario_alvo:
        flash('Usuário a ser removido não encontrado.', 'warning')
        return redirect(url_for('listar_usuarios'))

    pode_remover = False
    mensagem_erro_permissao = 'Você não tem permissão para remover este tipo de usuário.'

    if editor_tipo == 'master-admin':
        # Master-admin não pode remover outro master-admin se for o único ativo restante
        if usuario_alvo['tipo'] == 'master-admin':
            if usuario_alvo['id'] == editor_id: # Já coberto acima, mas por segurança
                pode_remover = False
                mensagem_erro_permissao = 'Você não pode remover a si mesmo!'
            else:
                cursor.execute("SELECT COUNT(*) FROM usuarios WHERE tipo = 'master-admin' AND ativo = 1 AND id != ?", (id_usuario_alvo,))
                count_outros_master_admins_ativos = cursor.fetchone()[0]
                if count_outros_master_admins_ativos >= 1:
                    pode_remover = True
                else:
                    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE tipo = 'master-admin' AND ativo = 1")
                    total_master_admins_ativos = cursor.fetchone()[0]
                    if total_master_admins_ativos > 1:
                        pode_remover = True
                    else:
                        pode_remover = False
                        mensagem_erro_permissao = 'Não é possível remover o único Master Administrador ativo ou deixar o sistema sem Master Administradores ativos.'
        else:
            # Master-admin pode remover admin, manutencao, solicitante
            pode_remover = True
    
    elif editor_tipo == 'admin':
        # Admin NÃO PODE remover master-admin
        if usuario_alvo['tipo'] == 'master-admin':
            pode_remover = False
            mensagem_erro_permissao = 'Administradores não podem remover usuários Master Administrador.'
        # Admin NÃO PODE remover outros admins
        elif usuario_alvo['tipo'] == 'admin':
            pode_remover = False
            mensagem_erro_permissao = 'Administradores não podem remover outros Administradores.'
        # Admin PODE remover solicitante e manutencao
        elif usuario_alvo['tipo'] in ['solicitante', 'manutencao']:
            pode_remover = True
        else:
            pode_remover = False # Por segurança, nega outros casos

    if not pode_remover:
        flash(mensagem_erro_permissao, 'danger')
        return redirect(url_for('listar_usuarios'))

    try:
        cursor.execute("SELECT COUNT(*) FROM ordens_servico WHERE solicitante_id = ? OR tecnico_id = ?", (id_usuario_alvo, id_usuario_alvo))
        if cursor.fetchone()[0] > 0:
            flash(f"Não é possível remover o usuário (ID: {id_usuario_alvo}) pois ele está associado a Ordens de Serviço. Considere desativá-lo.", 'warning')
            return redirect(url_for('listar_usuarios'))

        cursor.execute("SELECT COUNT(*) FROM registros_manutencao_direta WHERE criado_por_id = ? OR concluido_por_admin_id = ?", (id_usuario_alvo, id_usuario_alvo))
        if cursor.fetchone()[0] > 0:
            flash(f"Não é possível remover o usuário (ID: {id_usuario_alvo}) pois ele está associado a Registros de Manutenção. Considere desativá-lo.", 'warning')
            return redirect(url_for('listar_usuarios'))

        cursor.execute("DELETE FROM participantes_os WHERE tecnico_id = ?", (id_usuario_alvo,))
        cursor.execute("DELETE FROM participantes_registro_direto WHERE tecnico_id = ?", (id_usuario_alvo,))
 
        
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_usuario_alvo,))
        conn.commit()
        flash('Usuário removido com sucesso!', 'success')
    except sqlite3.IntegrityError as e:
        flash(f"Erro de integridade ao remover usuário: {str(e)}. Verifique se o usuário está referenciado em outras tabelas.", 'danger')
    except Exception as e:
        flash(f'Erro ao remover usuário: {str(e)}', 'danger')
    
    return redirect(url_for('listar_usuarios'))

# No final do arquivo, antes do app.run()
app.teardown_appcontext(close_db)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)