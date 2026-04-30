# Guia Dev

## Convenções
- Regras em `services`, não em templates
- Dependências de auth/tenant em `core/deps.py`
- Novos endpoints API em `app/routers`
- Migrações via Alembic

## Padrões
- Mensagens de erro consistentes
- `response_model` em rotas API
- Testes para cada bugfix/feature crítica
