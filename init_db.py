import sqlite3
from werkzeug.security import generate_password_hash

def criar_banco_dados():
    """Cria a estrutura do banco de dados sem dados de teste"""
    try:
        conn = sqlite3.connect('db/os.db')
        cursor = conn.cursor()

        # Configurações do banco
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA busy_timeout = 5000")

        # Tabela de usuários
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

        # Tabela de ordens de serviço
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            equipamento TEXT NOT NULL,
            problema TEXT NOT NULL,
            prioridade TEXT NOT NULL CHECK(prioridade IN ('baixa', 'normal', 'alta', 'urgente')),
            status TEXT NOT NULL CHECK(status IN ('Aberta', 'Agendada', 'Em andamento', 'Pausada', 'Concluída', 'Cancelada')) DEFAULT 'Aberta',
            solucao TEXT,
            tempo_reparo REAL,
            inicio TEXT,
            fim TEXT,
            solicitante_id INTEGER NOT NULL,
            tecnico_id INTEGER,
            local TEXT,
            setor TEXT,
            data_agendamento TEXT,
            horario_agendamento TEXT,
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
        CREATE TABLE IF NOT EXISTS participantes_os (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            os_id INTEGER NOT NULL,
            tecnico_id INTEGER NOT NULL,
            data_inclusao TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (os_id) REFERENCES ordens_servico(id) ON DELETE CASCADE,
            FOREIGN KEY (tecnico_id) REFERENCES usuarios(id)
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
        # Tabela de locais
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS locais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            ativo BOOLEAN DEFAULT 1,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("Tabela 'locais' verificada/criada.")

        # Apenas cria o usuário admin inicial
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
            INSERT INTO usuarios (usuario, senha, tipo, nome, email)
            VALUES (?, ?, ?, ?, ?)
            ''', ('admin', generate_password_hash('admin123'), 'admin', 'Administrador', 'admin@empresa.com'))

        conn.commit()
        print("\nBanco de dados criado com sucesso!")
        print("Usuário admin inicial:")
        print("- Login: admin")
        print("- Senha: admin123\n")

    except sqlite3.Error as e:
        print(f"\nErro ao criar banco de dados: {str(e)}\n")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    criar_banco_dados()