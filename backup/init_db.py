import sqlite3
from werkzeug.security import generate_password_hash

def criar_banco_dados():
    conn = None
    try:
        conn = sqlite3.connect('db/os.db')
        cursor = conn.cursor()

        # Configurações do banco
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL") # Mantido
        cursor.execute("PRAGMA busy_timeout = 5000") # Mantido

        print("\n--- Modificando Tabela usuarios ---")
        cursor.execute("DROP TABLE IF EXISTS usuarios") # CUIDADO: Apaga dados!
        cursor.execute('''
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('solicitante', 'manutencao', 'admin', 'master-admin')),
            nome TEXT NOT NULL,
            email TEXT UNIQUE,
            especialidade TEXT CHECK(especialidade IS NULL OR especialidade IN ('eletricista', 'mecanico')), -- Nova coluna
            ativo BOOLEAN DEFAULT 1,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("Tabela 'usuarios' recriada/verificada com sucesso.")

        print("\n--- Modificando Tabela ordens_servico ---")
        # Tabela de ordens de serviço
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Data de abertura da OS
            equipamento TEXT NOT NULL,
            problema TEXT NOT NULL,
            prioridade TEXT NOT NULL CHECK(prioridade IN ('baixa', 'normal', 'alta', 'urgente')),
            status TEXT NOT NULL CHECK(status IN ('Aberta', 'Agendada', 'Em andamento', 'Pausada', 'Concluída', 'Cancelada')) DEFAULT 'Aberta',
            solucao TEXT,
            tempo_reparo REAL, -- Em minutos ou horas, a ser calculado
            inicio TEXT,      -- Data/Hora de início do trabalho (pode ser manual ou automático)
            fim TEXT,         -- Data/Hora de conclusão do trabalho (AGORA SERÁ MANUAL)
            solicitante_id INTEGER NOT NULL,
            tecnico_id INTEGER, -- Pode representar o técnico principal ou o que iniciou
            local TEXT,
            setor TEXT,
            data_agendamento TEXT,
            horario_agendamento TEXT,
            FOREIGN KEY (solicitante_id) REFERENCES usuarios (id),
            FOREIGN KEY (tecnico_id) REFERENCES usuarios (id)
        )
        ''')
        print("Tabela 'ordens_servico' verificada/criada.")

        # Tabela de participantes da OS (existente e adequada)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS participantes_os (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            os_id INTEGER NOT NULL,
            tecnico_id INTEGER NOT NULL, -- ID do usuário técnico que participou
            data_inclusao TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (os_id) REFERENCES ordens_servico(id) ON DELETE CASCADE,
            FOREIGN KEY (tecnico_id) REFERENCES usuarios(id)
        )
        ''')
        print("Tabela 'participantes_os' verificada/criada.")


        print("\n--- Criando Nova Tabela registros_manutencao_direta ---")
        # Nova tabela para Registros de Manutenção Direta
        cursor.execute("DROP TABLE IF EXISTS participantes_registro_direto") # Se for recriar
        cursor.execute("DROP TABLE IF EXISTS registros_manutencao_direta") # Se for recriar
        cursor.execute('''
        CREATE TABLE registros_manutencao_direta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Quando o registro foi criado no sistema
            data_execucao TEXT NOT NULL,               -- Data e Hora que o serviço foi executado (manual)
            duracao_minutos INTEGER,                   -- Duração da manutenção em minutos (manual)
            equipamento_afetado TEXT,
            descricao_servico TEXT NOT NULL,
            observacoes TEXT,
            criado_por_id INTEGER NOT NULL,             -- ID do usuário de manutenção que criou
            status TEXT NOT NULL CHECK(status IN ('Pendente Aprovacao', 'Concluido', 'Cancelado')) DEFAULT 'Pendente Aprovacao',
            data_conclusao_admin TEXT,                 -- Data que o admin aprovou/concluiu
            concluido_por_admin_id INTEGER,            -- ID do admin que aprovou/concluiu
            FOREIGN KEY (criado_por_id) REFERENCES usuarios (id),
            FOREIGN KEY (concluido_por_admin_id) REFERENCES usuarios (id)
        )
        ''')
        print("Tabela 'registros_manutencao_direta' criada com sucesso.")

        # Tabela para participantes dos Registros de Manutenção Direta (opcional, mas recomendado)
        cursor.execute('''
        CREATE TABLE participantes_registro_direto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registro_id INTEGER NOT NULL,
            tecnico_id INTEGER NOT NULL, -- ID do usuário técnico que participou
            data_inclusao TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (registro_id) REFERENCES registros_manutencao_direta(id) ON DELETE CASCADE,
            FOREIGN KEY (tecnico_id) REFERENCES usuarios(id)
        )
        ''')
        print("Tabela 'participantes_registro_direto' criada com sucesso.")


        # Tabela de histórico da OS (existente)
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
        print("Tabela 'historico_os' verificada/criada.")

        # Tabela de locais (existente da alteração anterior)
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
        
        # Tabela de anexos da OS (existente)
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
        print("Tabela 'anexos_os' verificada/criada.")


        # Criação do usuário master-admin inicial se não existir (ou se a tabela foi recriada)
        # E um usuário admin padrão
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE tipo = 'master-admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
            INSERT INTO usuarios (usuario, senha, tipo, nome, email, ativo)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', ('masteradmin', generate_password_hash('master123'), 'master-admin', 'Master Administrador', 'master@empresa.com', 1))
            print("Usuário 'masteradmin' criado.")

        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE usuario = 'admin'")
        if cursor.fetchone()[0] == 0: # Se o admin padrão foi apagado ao dropar a tabela
             cursor.execute('''
            INSERT INTO usuarios (usuario, senha, tipo, nome, email, ativo)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', generate_password_hash('admin123'), 'admin', 'Administrador Padrão', 'admin@empresa.com', 1))
        print("Usuário 'admin' padrão recriado.")

        conn.commit()
        print("\nBanco de dados verificado/atualizado com sucesso!")
        print("Lembre-se: Se a tabela 'usuarios' foi recriada, todos os usuários anteriores foram perdidos.")
        print("Usuários iniciais:")
        print("- Login: masteradmin / Senha: master123")
        print("- Login: admin / Senha: admin123 (se recriado)")


    except sqlite3.Error as e:
        print(f"\nErro ao interagir com o banco de dados: {str(e)}\n")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # ATENÇÃO: Executar este script irá APAGAR e RE CRIAR a tabela USUARIOS se ela for dropada.
    print("Este script irá modificar o schema do banco de dados.")
    print("A tabela 'usuarios' será RECRIADA, o que APAGARÁ todos os usuários existentes.")
    confirmacao = input("Deseja continuar? (s/N): ")
    if confirmacao.lower() == 's':
        criar_banco_dados()
    else:
        print("Operação cancelada.")