# Chat Moderado - Backend

Sistema de chat em tempo real com moderação assíncrona de mensagens, construído com foco em escalabilidade, resiliência e alta performance.

## Como Executar

### Desenvolvimento
O ambiente de desenvolvimento utiliza Docker Compose com suporte a hot-reload.

1. **Pré-requisitos**: Docker e Docker Compose instalados.
2. **Configuração**: Certifique-se de que o arquivo `.env` existe na raiz.
3. **Execução**:
   ```bash
   docker-compose up --build
   ```
   O serviço estará disponível em `http://localhost:8000`.

### Produção
A configuração de produção utiliza imagens multi-stage e servidores de aplicação de alta performance.

1. **Configuração**: Crie um arquivo `.env.prod`.
2. **Execução**:
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```
   Em produção, o sistema utiliza **Gunicorn** com workers **Uvicorn** (`gunicorn app.asgi:application -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000`), garantindo o suporte nativo a protocolos assíncronos (ASGI) com a robustez do Gunicorn.

## Decisões Técnicas e Arquitetura

### 1. Stack e Frameworks
- **Django 5.2**: Escolhido por ser a versão mais estável e recente, oferecendo melhorias significativas em suporte assíncrono e performance de ORM.
- **Django Channels**: Utilizado para gerenciar a comunicação bidirecional via WebSockets.
- **Celery + RabbitMQ**: Orquestração de tarefas assíncronas (moderação) com garantia de entrega.

### 2. Fluxo de Mensagens e Moderação
O sistema utiliza uma abordagem de consistência eventual para garantir que o chat permaneça fluido enquanto o conteúdo é analisado:
- **Identificação no Frontend**: Ao enviar uma mensagem, o WebSocket retorna imediatamente um evento `message_queued` contendo o `id` da mensagem criada no banco. Isso permite que o frontend atualize o estado local da mensagem de "enviando" para "pendente" de forma precisa.
- **Isolamento de Processamento**: A moderação ocorre em background. Se aprovada, a mensagem é enviada a todos na sala via Channel Layer. Se rejeitada, apenas o autor recebe a notificação, evitando poluição visual para os demais usuários.
- **ModerationLog**: Todas as decisões de moderação (veredicto, score, provedor) são persistidas nesta entidade, permitindo auditoria completa e análise histórica do comportamento de filtros de conteúdo.

### 3. Escalabilidade e Performance
- **Cursor-based Pagination**: Para a listagem de mensagens, optamos por `CursorPagination`. Diferente do `OffsetPagination`, ele é imutável em relação a novas inserções, o que é essencial para implementar **scroll infinito** no frontend sem duplicação de itens.
- **Idempotência**: O processamento de moderação utiliza `select_for_update` (Pessimistic Locking) no banco de dados para garantir que, mesmo em cenários de retries agressivos ou concorrência pesada de workers, uma mensagem nunca seja processada duas vezes simultaneamente.

### 4. Estratégia de Testes
O projeto mantém uma separação clara entre tipos de testes para otimizar o ciclo de feedback no CI:
- **Testes Unitários**: Focam na lógica de negócio pura (services, logic) e rodam de forma isolada e rápida.
- **Testes de Integração**: Validam o fluxo completo, incluindo handshakes de WebSocket, persistência real em banco de dados e disparo de tasks Celery (mockadas em sua execução, mas validadas em seu disparo).
No pipeline do GitHub Actions, essas etapas rodam em steps separados para facilitar a identificação de falhas de lógica versus falhas de infraestrutura.

### 5. Observabilidade
- **Logs Estruturados**: Implementação com `structlog` gerando JSON em produção, permitindo integração direta com ferramentas de log aggregation (ELK, Datadog).
