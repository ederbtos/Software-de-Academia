# QA Automation e One-Click

## Arquitetura proposta
- Testes em `tests/` por camada (security, service, integration, e2e)
- Endpoint interno superadmin para disparar execução
- Job assíncrono com captura de logs e status

## Execução
- CI/CD: `pytest -q tests`
- UI superadmin: botão `Executar Testes`

## Segurança
- Endpoint protegido por `require_superadmin`
- Não executar em base de produção sem ambiente isolado

## Próximos incrementos
- Persistir histórico de execuções no banco
- Exibir progresso em tempo real por polling
- Adicionar testes E2E com Playwright em ambiente staging
