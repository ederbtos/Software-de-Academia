# Testes

## Estratégia
- Unitários: funções puras e serviços
- Integração: serviço + banco isolado
- E2E: fluxos web/API principais

## Implementado no repositório
- Pasta `tests/` com suíte pytest
- Runner assíncrono one-click no superadmin
- Execução CI/CD: `pytest -q tests`
- Auditoria de acessibilidade WCAG2AA com Pa11y CI (`.github/workflows/accessibility.yml`, `.pa11yci.json`)
  - Cobertura pública: `/login`, `/auth/esqueci-senha`
  - Cobertura autenticada (login automatizado): `/superadmin`, `/superadmin/auditoria`, `/dashboard`, `/alunos`, `/matriculas`, `/planos`, `/funcionarios`, `/relatorios`, `/aulas`, `/treinos`, `/avaliacoes`, `/exercicios`, `/configuracoes`
  - Gate de CI em 2 camadas:
    - `pa11y-strict` (bloqueante): rotas críticas com `--threshold 0`
    - `pa11y-monitoring` (não bloqueante): cobertura ampliada com relatório contínuo
  - Artefatos no GitHub Actions:
    - `pa11y-monitoring-report` com saída JSON consolidada por execução
    - `pa11y-baseline-summary` com comparação entre baseline e execução atual
  - Regressão de acessibilidade:
    - Configuração em `.pa11y-baseline.json`
    - Campos: `total_issues_baseline`, `allowed_delta_abs`, `allowed_delta_pct`
    - Suporte a baseline por rota (`routes.<url>.baseline` + deltas por rota)
    - Se a execução ultrapassar o limite calculado (global ou por rota), o job de monitoring sinaliza regressão

## Cobertura alvo
- Auth e permissões
- CRUD core (alunos, planos, matrículas, pagamentos, aulas)
- Fluxos críticos (inadimplência, treino, check-in)
