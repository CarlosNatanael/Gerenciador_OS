import sqlite3
from werkzeug.security import generate_password_hash

def criar_banco_dados():
    conn = None
    try:
        conn = sqlite3.connect('db/os.db')
        cursor = conn.cursor()

        # Configurações do banco
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA busy_timeout = 5000")

        print("\n--- Modificando Tabela usuarios ---")
        cursor.execute("DROP TABLE IF EXISTS usuarios")
        print("Tabela 'usuarios' removida (se existia).")
        cursor.execute('''
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('solicitante', 'manutencao', 'admin', 'master-admin')),
            nome TEXT NOT NULL,
            email TEXT UNIQUE,
            ativo BOOLEAN DEFAULT 1,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("Tabela 'usuarios' recriada com sucesso.")

        print("\n--- Criando Nova Tabela tecnicos ---")
        cursor.execute("DROP TABLE IF EXISTS tecnicos")
        cursor.execute('''
        CREATE TABLE tecnicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            tipo_tecnico TEXT NOT NULL CHECK(tipo_tecnico IN ('eletricista', 'mecanico')),
            ativo BOOLEAN DEFAULT 1,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("Tabela 'tecnicos' criada com sucesso.")

        print("\n--- Verificando/Criando Tabela ordens_servico ---")
        # Se a tabela já existir e o schema estiver correto, não precisa dropar.
        # Se precisar alterar o schema, seria melhor dropar ou usar ALTER TABLE.
        # cursor.execute("DROP TABLE IF EXISTS ordens_servico") # Descomente se precisar recriar do zero
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
            FOREIGN KEY (solicitante_id) REFERENCES usuarios (id) ON DELETE RESTRICT, -- Impede deleção de usuário com OS
            FOREIGN KEY (tecnico_id) REFERENCES usuarios (id) ON DELETE SET NULL -- Seta NULL se o usuário técnico for deletado
        )
        ''')
        print("Tabela 'ordens_servico' verificada/criada.")

        print("\n--- Recriando Tabela participantes_os ---")
        cursor.execute("DROP TABLE IF EXISTS participantes_os")
        cursor.execute('''
        CREATE TABLE participantes_os (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            os_id INTEGER NOT NULL,
            tecnico_ref_id INTEGER NOT NULL, 
            data_inclusao TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (os_id) REFERENCES ordens_servico(id) ON DELETE CASCADE,
            FOREIGN KEY (tecnico_ref_id) REFERENCES tecnicos(id) ON DELETE RESTRICT -- Impede deleção de técnico com OS
        )
        ''')
        print("Tabela 'participantes_os' recriada com sucesso.")

        print("\n--- Verificando/Criando Tabela registros_manutencao_direta ---")
        # cursor.execute("DROP TABLE IF EXISTS registros_manutencao_direta") # Descomente se precisar recriar
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros_manutencao_direta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            data_execucao TEXT NOT NULL,
            duracao_minutos INTEGER,
            equipamento_afetado TEXT,
            descricao_servico TEXT NOT NULL,
            observacoes TEXT,
            criado_por_id INTEGER NOT NULL, 
            status TEXT NOT NULL CHECK(status IN ('Pendente Aprovacao', 'Concluido', 'Cancelado')) DEFAULT 'Pendente Aprovacao',
            data_conclusao_admin TEXT,
            concluido_por_admin_id INTEGER,
            FOREIGN KEY (criado_por_id) REFERENCES usuarios (id) ON DELETE RESTRICT,
            FOREIGN KEY (concluido_por_admin_id) REFERENCES usuarios (id) ON DELETE SET NULL
        )
        ''')
        print("Tabela 'registros_manutencao_direta' verificada/criada.")

        print("\n--- Recriando Tabela participantes_registro_direto ---")
        cursor.execute("DROP TABLE IF EXISTS participantes_registro_direto")
        cursor.execute('''
        CREATE TABLE participantes_registro_direto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registro_id INTEGER NOT NULL,
            tecnico_ref_id INTEGER NOT NULL, 
            data_inclusao TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (registro_id) REFERENCES registros_manutencao_direta(id) ON DELETE CASCADE,
            FOREIGN KEY (tecnico_ref_id) REFERENCES tecnicos(id) ON DELETE RESTRICT
        )
        ''')
        print("Tabela 'participantes_registro_direto' recriada com sucesso.")

        print("\n--- Verificando/Criando Tabela historico_os ---")
        # cursor.execute("DROP TABLE IF EXISTS historico_os") # Descomente se precisar recriar
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
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL -- Seta NULL se usuário for deletado
        )
        ''')
        print("Tabela 'historico_os' verificada/criada.")

        print("\n--- Verificando/Criando Tabela locais ---")
        # cursor.execute("DROP TABLE IF EXISTS locais") # Descomente se precisar recriar
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
        
        print("\n--- Verificando/Criando Tabela anexos_os ---")
        # cursor.execute("DROP TABLE IF EXISTS anexos_os") # Descomente se precisar recriar
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
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
        )
        ''')
        print("Tabela 'anexos_os' verificada/criada.")

        print("\n--- Criando usuários padrão ---")
        cursor.execute("INSERT INTO usuarios (usuario, senha, tipo, nome, email, ativo) VALUES (?, ?, ?, ?, ?, ?)",
                       ('masteradmin', generate_password_hash('master123'), 'master-admin', 'Master Administrador', 'master@empresa.com', 1))
        print("Usuário 'masteradmin' criado.")

        cursor.execute("INSERT INTO usuarios (usuario, senha, tipo, nome, email, ativo) VALUES (?, ?, ?, ?, ?, ?)",
                       ('admin', generate_password_hash('admin123'), 'admin', 'Administrador Padrão', 'admin@empresa.com', 1))
        print("Usuário 'admin' padrão criado.")
        
        cursor.execute("INSERT INTO usuarios (usuario, senha, tipo, nome, email, ativo) VALUES (?, ?, ?, ?, ?, ?)",
                       ('manutencao', generate_password_hash('manutencao123'), 'manutencao', 'Equipe de Manutenção', 'manutencao@empresa.com', 1))
        print("Usuário genérico 'manutencao' criado com senha 'manutencao123'.")

        # Adicionar técnicos de exemplo
        tecnicos_exemplo = [
            ('Marcela', 'eletricista'),
            ('Luiz', 'mecanico'),
            ('Marcio', 'eletricista')
        ]
        # Usar INSERT OR IGNORE para evitar erro se os técnicos já existirem
        cursor.executemany("INSERT OR IGNORE INTO tecnicos (nome, tipo_tecnico) VALUES (?, ?)", tecnicos_exemplo)
        print(f"Técnicos de exemplo adicionados/ignorados na tabela 'tecnicos'.")

        conn.commit()
        print("\nBanco de dados atualizado com sucesso!")
        print("ATENÇÃO: Se tabelas foram RECRIADAS, dados antigos nelas foram perdidos.")

    except sqlite3.Error as e:
        print(f"\nErro ao interagir com o banco de dados: {str(e)}\n")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Este script irá modificar o schema do banco de dados.")
    print("AS SEGUINTES TABELAS SERÃO RECRIADAS (DROP e CREATE) SE JÁ EXISTIREM: usuarios, tecnicos, participantes_os, participantes_registro_direto.")
    print("TODOS OS DADOS NESSAS TABELAS SERÃO PERDIDOS.")
    print("Outras tabelas (ordens_servico, registros_manutencao_direta, historico_os, locais, anexos_os) serão criadas com 'IF NOT EXISTS'.")
    confirmacao = input("Deseja continuar com a operação? (s/N): ")
    if confirmacao.lower() == 's':
        criar_banco_dados()
    else:
        print("Operação cancelada pelo usuário.")