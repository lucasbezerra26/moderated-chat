# Chat Moderado - Backend

Sistema de chat em tempo real com moderação assíncrona de mensagens.

## 🚀 Como Executar

Copie o arquivo de variáveis de ambiente:

```bash
cp .env.example .env

```

### Ambiente de Desenvolvimento

Utiliza Docker Compose com *bind mounts* para hot-reload e debug facilitado.

```bash
docker-compose up -d --build

```

Disponível em: `http://localhost:8000`

### Ambiente de Produção

Utiliza construção *multi-stage* otimizada para segurança e tamanho de imagem.

```bash
docker-compose -f docker-compose.prod.yml up --build -d

```

**Nota sobre a Arquitetura de Servidor:**
Em produção, optou-se pela utilização do **Gunicorn** atuando como gerenciador de processos (process manager) para orquestrar workers **Uvicorn**. Essa abordagem delega ao Gunicorn a responsabilidade de monitoramento de processos, restarts e gerenciamento de sinais de sistema, enquanto os workers Uvicorn processam o protocolo ASGI de alta performance necessário para os WebSockets.

---

## 🏛 Decisões Arquiteturais e Técnicas

### 1. Stack Tecnológica

* **Django 5.2 + DRF**: Framework base, utilizado pela maturidade e ecossistema robusto.
* **Django Channels (ASGI)**: Para gerenciamento de conexões persistentes (WebSockets) e stateful communication.
* **Celery + Redis**: Fila de tarefas para processamento assíncrono da moderação, desacoplando a resposta da API do tempo de inferência da IA.
* **PostgreSQL**: Persistência relacional robusta.
* **Structlog**: Logs estruturados (JSON) para garantir observabilidade em ferramentas de agregação (Datadog/ELK).

### 2. Pipeline de Moderação e Consistência

A arquitetura resolve o desafio de moderar mensagens sem travar a interface do usuário (UI Blocking):

* **Feedback Otimista & Eventos de Estado**: O WebSocket não espera a moderação. Ele confirma o recebimento (`message_queued`) com o ID da mensagem. O Frontend exibe a mensagem como "Pendente".
* **Design Pattern na Moderação**: O sistema utiliza uma camada de serviço (Service Layer) para a moderação. Atualmente configurado com um *Mock/Regex Provider*, mas desenhado para fácil injeção de dependência de serviços externos (como Azure AI ou OpenAI) sem refatoração do domínio.
* **Auditoria (ModerationLog)**: Decisões de moderação não são efêmeras. Uma entidade dedicada persiste o *score*, o *veredicto* e o *provedor* utilizado, permitindo auditoria e *fine-tuning* futuro das regras.

### 3. Concorrência e Integridade de Dados

Para garantir a robustez em um ambiente distribuído com múltiplos workers:

* **Controle de Concorrência (Pessimistic Locking)**: A task do Celery utiliza `select_for_update()` ao processar a moderação. Isso garante a **Idempotência técnica** a nível de banco de dados, impedindo que "Race Conditions" (comuns em retries de fila) processem ou cobrem pela mesma mensagem duas vezes.
* **Paginação por Cursor**: A API de histórico utiliza `CursorPagination`. Essa decisão evita os problemas clássicos de `OffsetPagination` (mensagens puladas ou duplicadas) quando novos itens são inseridos no topo da lista durante o scroll do usuário.

## 🧪 Qualidade e Testes

O projeto segue uma pirâmide de testes focada em confiabilidade:

* **Unitários**: Focados em Services e Models, garantindo regras de negócio isoladas.
* **Integração**: Testes que sobem o banco de dados e validam o fluxo completo (Consumer -> DB -> Celery Task). Utiliza `pytest-asyncio` para validar o comportamento dos WebSockets.
