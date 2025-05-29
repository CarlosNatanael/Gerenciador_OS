## 🧩 Visão Geral

O Sistema de OS Web é uma aplicação voltada para a gestão de Ordens de Serviço (OS) da área de manutenção elétrica, com foco na organização, agilidade e rastreabilidade das operações. A ferramenta visa facilitar o processo desde a abertura da OS até sua conclusão, classificando cada solicitação como urgente ou programada.

---

## 🔍 Objetivo

Permitir que os três tipos de usuários envolvidos no processo de manutenção possam:
- Solicitar serviços com clareza.
- Executar manutenções com controle de tempo e etapas.
- Acompanhar estatísticas e informações detalhadas.

---

## 👥 Tipos de Usuários

1. **Solicitante**
   - Responsável por abrir as OSs.
   - Informa o tipo de problema e classifica a urgência.

2. **Manutenção Elétrica**
   - Recebe as OSs.
   - Realiza os serviços.
   - Preenche informações de execução e solução.

3. **Administrador**
   - Visualiza relatórios e métricas.
   - Monitora tempo de reparo, erros mais comuns e quantidade de OSs por período.

---

## 🧭 Fluxo Operacional

### 1. Abertura da OS
- Iniciada pelo Solicitante.
- Define a **classe** da OS:
  - **Urgente**
  - **Programado**

### 2. Classe Urgente
- Preenchimento de erros e data.
- Manutenção Elétrica realiza o serviço imediatamente.
- Após conclusão, é preenchido o que foi feito.
- Caso não resolva, a OS volta para o ciclo de manutenção.

### 3. Classe Programado
- Preenchimento de erros e data.
- Análise da OS pela equipe de manutenção.
- Agendamento de data para execução.
- Manutenção executa conforme agendado.
- Caso resolvido, preenche o que foi feito.
- Caso não resolvido, retorna ao agendamento.

---

## 📊 Recursos para o Administrador

- Dashboard com estatísticas:
  - Quantidade de OSs abertas e concluídas.
  - Tempo médio de reparo.
  - Erros mais recorrentes.
  - OSs pendentes ou reabertas.
- Filtros por período, setor e tipo de OS.

---

## 🔧 Funcionalidades Técnicas Planejadas

- Login por tipo de usuário (Solicitante, Manutenção, Administrador).
- Sistema responsivo (desktop e mobile).
- Banco de dados relacional (ex: PostgreSQL ou SQLite).
- Registro automático de datas de início e fim da OS.
- Cálculo do tempo de reparo.
- Exportação de relatórios (CSV ou PDF).
"""