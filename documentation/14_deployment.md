# Deploy

## Local
1. Configurar `.env`
2. `docker compose up -d --build`
3. Aplicar migrações (Dockerfile já executa `alembic upgrade head`)

## Variáveis essenciais
- `database_url`
- `secret_key`
- `superadmin_email`
- `superadmin_password`
- SMTP (`smtp_host`, `smtp_user`, ...)

## Produção
- HTTPS obrigatório
- segredo forte e rotacionável
- backup do PostgreSQL
