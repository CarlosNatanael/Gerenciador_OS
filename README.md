# Sistema de Gerenciamento de Ordens de Serviço (OS)

## 🧩 Visão Geral

O Sistema de Gerenciamento de OS Web é uma aplicação desenvolvida em Flask para a gestão completa de Ordens de Serviço (OS) e registros de manutenção, com foco na organização, agilidade, rastreabilidade das operações e personalização para as necessidades das empresas de indústria. A ferramenta facilita o processo desde a solicitação ou registro de um serviço até sua conclusão e análise, envolvendo diferentes perfis de usuários com permissões específicas.

---

## 🔍 Objetivos Principais

* Permitir que **Solicitantes** abram OSs de forma clara e objetiva.
* Capacitar a equipe de **Manutenção** (utilizando um login compartilhado) a receber, agendar, executar serviços e registrar trabalhos diretos, selecionando os técnicos individuais participantes.
* Fornecer aos **Administradores** e **Master Administradores** ferramentas para monitorar o fluxo de trabalho, gerenciar usuários, técnicos, locais, aprovar registros e extrair relatórios e métricas detalhadas.
* Melhorar a comunicação e o controle sobre as atividades de manutenção.
* Oferecer uma interface moderna, responsiva e com opções de personalização (tema Light/Dark).

---

## 👥 Tipos de Usuários e Suas Funcionalidades

O sistema define quatro tipos principais de usuários do sistema (com login) e um cadastro de técnicos individuais (sem login, gerenciados pelos administradores):

1.  **Solicitante:**
    * Abrir novas Ordens de Serviço (OS), especificando equipamento, local, setor, problema e prioridade (Normal/Urgente).
    * Visualizar o status das suas OSs abertas.

2.  **Manutenção (Login Compartilhado):**
    * Utiliza um login único para toda a equipe de manutenção.
    * Visualizar o painel com todas as OSs pendentes, agendadas ou em andamento.
    * **Agendar OS:** Definir data e hora para a execução de uma OS recebida.
    * **Iniciar Reparo de OS:** Marcar uma OS agendada como "Em andamento".
    * **Concluir OS:**
        * Registrar a solução aplicada.
        * Informar manualmente a data e hora da conclusão efetiva do serviço.
        * Selecionar, a partir de uma lista de técnicos cadastrados (Eletricistas e Mecânicos), quais indivíduos participaram da execução da OS.
    * **Criar Registros de Manutenção Direta:**
        * Registrar trabalhos de manutenção realizados que não foram originados por uma OS formal.
        * Informar data/hora da execução, duração, equipamento, descrição do serviço, observações e os técnicos individuais participantes.
        * Estes registros ficam pendentes de aprovação pelo administrador.

3.  **Administrador (Admin):**
    * Acesso ao Dashboard Administrativo com estatísticas de OS e Registros de Manutenção Direta.
    * Visualizar detalhes de todas as OSs e Registros de Manutenção Direta.
    * **Gerenciar Usuários:**
        * Criar, listar, editar e ativar/desativar usuários dos tipos: Solicitante e Login da Manutenção.
        * Não pode criar ou modificar outros Administradores ou Master Administradores.
    * **Gerenciar Técnicos Individuais:**
        * Criar, listar, editar e ativar/desativar técnicos individuais (Eletricistas, Mecânicos) que são selecionados nas OSs e Registros.
    * **Gerenciar Locais:**
        * Criar, listar, editar e ativar/desativar locais que podem ser selecionados na abertura de OS.
    * **Processar Registros de Manutenção Direta:**
        * Visualizar registros criados pela equipe de manutenção.
        * Aprovar/Concluir ou Cancelar esses registros.
    * Gerar Relatório de OS em formato Excel.
    * Acessar a página de Configurações Gerais do sistema.
    * Pode abrir OSs (atuando como solicitante).

4.  **Master Administrador (Master-Admin):**
    * Possui todas as funcionalidades de um Administrador.
    * **Privilégio Adicional:** É o único tipo de usuário que pode criar, editar e gerenciar outros usuários do tipo Administrador.
    * Responsável pela configuração de alto nível do sistema e gerenciamento de todos os tipos de usuários.

---

## 🛠️ Técnicos Individuais (Gerenciados, sem login próprio)

* São cadastrados pelos Administradores/Master Administradores.
* Campos: Nome, Tipo (Eletricista ou Mecânico), Status (Ativo/Inativo).
* São selecionados nos formulários de conclusão de OS e criação de Registros de Manutenção Direta para indicar quem efetivamente participou do trabalho.

---

## 🧭 Fluxos Operacionais Principais

### 1. Fluxo de Ordem de Serviço (OS)
    * **Abertura:** Iniciada pelo Solicitante (ou Admin/Master-Admin). Define equipamento, local, setor, problema e prioridade.
    * **Recebimento pela Manutenção:** A equipe de manutenção visualiza a OS no painel.
    * **Agendamento (pela Manutenção):** A equipe de manutenção define a data e hora para o reparo. O status da OS muda para "Agendada". O usuário do sistema (login 'manutencao') que agendou é registrado.
    * **Início do Reparo (pela Manutenção):** A OS é marcada como "Em andamento".
    * **Conclusão (pela Manutenção):**
        * A equipe registra a solução.
        * Informa manualmente a data e hora da conclusão.
        * Seleciona os técnicos individuais (Eletricistas/Mecânicos) que participaram.
        * O status da OS muda para "Concluída". O tempo de reparo é calculado.
    * **Visualização pelo Admin/Master-Admin:** Acompanhamento completo do ciclo da OS.

### 2. Fluxo de Registro de Manutenção Direta
    * **Criação (pela Manutenção):** A equipe de manutenção (usando o login compartilhado) cria um novo registro, informando data/hora da execução, duração, equipamento, descrição, observações e os técnicos individuais participantes.
    * **Status Inicial:** "Pendente Aprovação".
    * **Processamento pelo Admin/Master-Admin:**
        * Visualiza os detalhes do registro.
        * Pode "Concluir/Aprovar" o registro (status muda para "Concluido") ou "Cancelar" o registro.
        * A data e o admin que processou são registrados.

---

## 📊 Recursos para Administradores (Admin e Master-Admin)

* **Dashboard Centralizado:**
    * Estatísticas de Ordens de Serviço: Total, Abertas, Concluídas, Em Andamento, Agendadas, Tempo Médio de Reparo.
    * Estatísticas de Registros de Manutenção Direta: Total, Pendentes de Aprovação.
* **Ações Rápidas:** Links para as principais funcionalidades de gerenciamento.
* **Listagem e Detalhamento:** Visualização completa de todas as OSs e todos os Registros de Manutenção Direta.
* **Gerenciamento Completo:**
    * Usuários do sistema (com controle hierárquico entre Master-Admin e Admin).
    * Técnicos individuais (Eletricistas/Mecânicos).
    * Locais para OS.
* **Exportação de Relatórios:** Geração de relatório de OS em formato Excel.
* **Configurações:** Acesso a configurações gerais do sistema (expansível).

---

## ✨ Interface e Experiência do Usuário

* **Navegação Lateral (Offcanvas):** Menu principal retrátil para otimizar o espaço e modernizar a navegação.
* **Tema Light/Dark:** Opção para o usuário alternar entre um tema claro e um tema escuro, com preferência salva no navegador.
* **Interface Responsiva:** Adaptável para uso em desktops e dispositivos móveis.
* **Feedback ao Usuário:** Mensagens de sucesso, erro e aviso (flash messages).

---

## 🔧 Estrutura Técnica e Banco de Dados

* **Backend:** Flask (Python)
* **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
* **Banco de Dados:** SQLite
* **Principais Tabelas:**
    * `usuarios`: Armazena os usuários do sistema com login (Solicitante, Manutenção, Admin, Master-Admin).
    * `tecnicos`: Cadastra os técnicos individuais (Nome, Tipo: Eletricista/Mecânico, Ativo).
    * `ordens_servico`: Detalhes das OSs, incluindo quem solicitou, quem agendou/iniciou no sistema, datas, status, solução, etc.
    * `participantes_os`: Tabela de ligação entre `ordens_servico` e `tecnicos` para registrar quem participou em cada OS.
    * `registros_manutencao_direta`: Detalhes dos registros de manutenção feitos pela equipe sem OS formal.
    * `participantes_registro_direto`: Tabela de ligação entre `registros_manutencao_direta` e `tecnicos`.
    * `historico_os`: Log de alterações importantes nas OSs.
    * `locais`: Cadastro de locais para seleção na abertura de OS.
    * `anexos_os` (se implementado): Para anexar arquivos às OSs.

---

## 🚀 Como Executar (Exemplo Básico)

1.  **Pré-requisitos:**
    * Python 3.x
    * pip (gerenciador de pacotes Python)
2.  **Instalação de Dependências:**
    ```bash
    pip install Flask Werkzeug openpyxl
    ```
3.  **Inicialização do Banco de Dados:**
    * Execute o script `init_db.py` para criar o banco de dados e as tabelas (atenção: recria algumas tabelas, apagando dados existentes nelas).
    ```bash
    python init_db.py
    ```
    * Confirme a operação quando solicitado.
4.  **Executar a Aplicação Flask:**
    ```bash
    flask run
    # Ou, se seu arquivo principal for app.py:
    # python app.py
    ```
5.  Acesse a aplicação no seu navegador (geralmente `http://127.0.0.1:5000/`).

**Usuários Padrão (criados pelo `init_db.py`):**
* Master Administrador: `masteradmin` / `master123`
* Administrador Padrão: `admin` / `admin123`
* Login Compartilhado da Manutenção: `manutencao` / `manutencao123`

---