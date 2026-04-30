# Segurança

## Implementado
- Hash de senha com `bcrypt`
- JWT assinado
- Cookie `httponly`
- Autorização por papel e escopo

## Melhorias recomendadas
- `secure=True` em cookie em produção
- proteção CSRF em formulários
- remover credencial padrão de superadmin
- padronizar tratamento de exceções sem vazar detalhes
