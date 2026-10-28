# Bancos locais

Esta pasta contém o schema relacional usado diretamente por `app/tools/financeiro.py` e `app/tools/agenda.py`.

1. Copie `.env.example` para `.env`. Substitua `change-me-local` pelo mesmo valor em `POSTGRES_PASSWORD` e `DATABASE_URL`.
2. Preencha as chaves reais `GEMINI_API_KEY`, `GROQ_API_KEY` e `TYPESAFE_API_KEY`. Para o Google Calendar MCP, disponibilize `gcp-oauth.keys.json` na raiz do projeto; a primeira autenticação pode ser feita com `python -c "from app.tools.calendario_google import autenticar; print(autenticar())"`.
3. Inicie os bancos com `docker compose up -d` e aguarde o PostgreSQL ficar saudável e o serviço `qdrant-init` concluir.
4. Execute a API no host, para que `localhost` e as portas publicadas do Compose coincidam com as URLs configuradas.
5. Para carregar o FAQ no Qdrant usando os embeddings reais do Gemini, execute `python -m app.ingest` na raiz do projeto.

O PostgreSQL executa `01-schema.sql` apenas na criação inicial do volume. O MongoDB cria o banco e as collections durante o uso. O serviço `qdrant-init` cria as três collections de 768 dimensões esperadas pelo código (`memoria_perfil`, `memoria_resumos` e `faq_chuncks`) sem recriar as que já existem.

O código da aplicação continua usando os APIs reais do Gemini, Groq, TypeSafe/JEV e Google Calendar MCP; apenas os bancos são locais. As chaves e as credenciais OAuth não estão incluídas neste repositório.
