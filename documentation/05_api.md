# API

## Base
- Prefixo: `/api/v1`

## Auth
- `POST /auth/login`
- `POST /auth/login/academia`
- `POST /auth/logout`

## Superadmin
- `GET /superadmin/academias`
- `POST /superadmin/academias`
- `PATCH /superadmin/academias/{academia_id}`
- `POST /superadmin/usuarios`

## Tenant (resumo)
- Dashboard: `GET /dashboard`
- Alunos: `GET/POST/PATCH /alunos`
- Matrículas: `POST /matriculas`
- Pagamentos: `PATCH /pagamentos/{id}/pagar`
- Presenças: `POST /presencas`, `GET /presencas/aluno/{id}`
- Avaliações: `POST /avaliacoes`, `GET /avaliacoes/aluno/{id}`
- Exercícios: `GET/POST /exercicios`
- Treinos: `POST /treinos`, `GET /treinos/*`
- Aulas: `GET/POST /aulas`, `POST/DELETE /aulas/inscricao`
- Planos: `GET/POST/PATCH /planos`
- Funcionários: `GET/POST/PATCH /funcionarios`

## Exemplo
```json
POST /api/v1/alunos
{"nome":"Maria","email":"maria@x.com"}
```
