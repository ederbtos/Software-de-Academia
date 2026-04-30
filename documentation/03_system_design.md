# System Design

## Componentes principais
- `main.py`: rotas web, autenticação via cookie JWT e páginas
- `app/routers/public.py`: API pública/superadmin
- `app/routers/tenant.py`: API operacional da academia
- `app/core/deps.py`: auth e resolução de tenant
- `app/services/*`: regras por domínio

## Comunicação entre módulos
`Route -> Dependency(Auth/Tenant) -> Service -> ORM -> DB -> Response`

## Decisões arquiteturais
- Token JWT com `scope` (`public`/`tenant`) e `schema` para contexto de academia
- Tabelas públicas em schema `public`; dados operacionais sem schema explícito (resolvidos via `search_path`)
- Scheduler diário para vencimentos/notificações
