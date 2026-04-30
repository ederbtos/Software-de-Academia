# Regras de Negócio

- `slug` de academia: regex `^[a-z0-9-]{3,60}$`
- Academia nova cria schema `academia_{slug}`
- Matrícula ativa gera pagamento pendente inicial
- Pagamento em atraso compõe inadimplência
- Lista de espera em aula quando excede capacidade
- Cancelamento de inscrição promove próximo da espera
- Somente usuários ativos autenticam
- Escopos JWT: `public` e `tenant`
- Papéis controlam acesso (RBAC)
