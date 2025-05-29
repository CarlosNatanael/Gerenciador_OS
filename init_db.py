import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

def criar_banco_dados():
    """Cria e popula o banco de dados do sistema de OS"""
    try:
        # Conecta ao banco de dados (cria se não existir)
        conn = sqlite3.connect('db/os.db')
        cursor = conn.cursor()

        # Configurações do banco para melhor performance
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA busy_timeout = 5000")

        # Criação das tabelas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('solicitante', 'manutencao', 'admin')),
            nome TEXT NOT NULL,
            email TEXT UNIQUE,
            ativo BOOLEAN DEFAULT 1,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            equipamento TEXT NOT NULL,
            problema TEXT NOT NULL,
            prioridade TEXT NOT NULL CHECK(prioridade IN ('baixa', 'normal', 'alta', 'urgente')),
            status TEXT NOT NULL CHECK(status IN ('Aberta', 'Em andamento', 'Pausada', 'Concluída', 'Cancelada')) DEFAULT 'Aberta',
            solucao TEXT,
            tempo_reparo REAL,
            inicio TEXT,
            fim TEXT,
            solicitante_id INTEGER NOT NULL,
            tecnico_id INTEGER,
            local TEXT,
            setor TEXT,
            FOREIGN KEY (solicitante_id) REFERENCES usuarios (id),
            FOREIGN KEY (tecnico_id) REFERENCES usuarios (id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_os (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            os_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            data_alteracao TEXT DEFAULT CURRENT_TIMESTAMP,
            acao TEXT NOT NULL,
            observacao TEXT,
            campo_alterado TEXT,
            valor_anterior TEXT,
            novo_valor TEXT,
            FOREIGN KEY (os_id) REFERENCES ordens_servico (id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS anexos_os (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            os_id INTEGER NOT NULL,
            nome_arquivo TEXT NOT NULL,
            caminho_arquivo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            tamanho INTEGER NOT NULL,
            data_upload TEXT DEFAULT CURRENT_TIMESTAMP,
            usuario_id INTEGER NOT NULL,
            FOREIGN KEY (os_id) REFERENCES ordens_servico (id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
        ''')

        # Verifica se já existem usuários para não duplicar
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            # Inserindo usuários de teste com senhas hasheadas
            usuarios_teste = [
                ('solicitante', generate_password_hash('123456'), 'solicitante', 
                 'João Silva', 'joao@empresa.com'),
                ('tecnico', generate_password_hash('123456'), 'manutencao', 
                 'Carlos Souza', 'carlos@empresa.com'),
                ('admin', generate_password_hash('admin123'), 'admin', 
                 'Administrador', 'admin@empresa.com'),
                ('engenharia', generate_password_hash('eng123'), 'manutencao', 
                 'Engenaria Elétrica', 'engenharia@empresa.com')
            ]

            cursor.executemany('''
            INSERT INTO usuarios (usuario, senha, tipo, nome, email)
            VALUES (?, ?, ?, ?, ?)
            ''', usuarios_teste)

            # Inserindo OSs de exemplo
            agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            os_teste = [
                (agora, 'Motor Elétrico 10HP', 'Não está ligando', 'urgente', 'Aberta',
                 None, None, None, None, 1, None, 'Sala de Máquinas', 'Produção'),
                
                (agora, 'Quadro de Força', 'Disjuntor desarmando', 'alta', 'Aberta',
                 None, None, None, None, 1, None, 'Galpão 2', 'Armazenamento'),
                
                (agora, 'Iluminação Externa', 'Lâmpadas queimadas', 'normal', 'Em andamento',
                 'Troca de reator necessária', 45, agora, None, 1, 2, 'Área Externa', 'Manutenção'),
                
                (agora, 'CLP Linha 5', 'Falha comunicação', 'alta', 'Concluída',
                 'Reset do módulo de comunicação', 120, agora, agora, 1, 3, 'Linha de Produção 5', 'Produção')
            ]

            cursor.executemany('''
            INSERT INTO ordens_servico 
            (data, equipamento, problema, prioridade, status, solucao, tempo_reparo, 
             inicio, fim, solicitante_id, tecnico_id, local, setor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', os_teste)

            # Histórico de exemplo
            cursor.execute('''
            INSERT INTO historico_os 
            (os_id, usuario_id, acao, observacao, campo_alterado, valor_anterior, novo_valor)
            VALUES 
            (4, 2, 'Status alterado', 'Iniciado reparo', 'status', 'Aberta', 'Em andamento'),
            (4, 3, 'Status alterado', 'Reparo concluído', 'status', 'Em andamento', 'Concluída')
            ''')

        conn.commit()
        print("\nBanco de dados criado com sucesso!")
        print("Usuários de teste (senha entre parênteses):")
        print("- solicitante (123456) - Solicitante")
        print("- tecnico (123456) - Técnico de Manutenção")
        print("- admin (admin123) - Administrador")
        print("- engenharia (eng123) - Equipe de Engenharia\n")

    except sqlite3.Error as e:
        print(f"\nErro ao criar banco de dados: {e}\n")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    criar_banco_dados()