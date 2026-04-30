# Roadmap de Evolução (90 dias)

## Objetivo
Elevar o produto para padrão de mercado em segurança, UX, confiabilidade, escala e operação.

## Fase 1 (Dias 1-30) - Fundação
- [x] Hardening de sessão (cookie seguro, max_age, path)
- [x] Proteção CSRF em rotas web com formulário
- [x] Remoção de credencial sensível padrão (`superadmin_password` obrigatório em ambiente)
- [x] CI com execução automática de testes
- [x] Auditoria básica de ações críticas
- [x] Cobertura inicial de testes de serviços e API crítica
- [x] Execução one-click de testes no superadmin
- [x] Base de acessibilidade global no frontend (landmarks, foco visível, aria)
- [x] Gate de acessibilidade no CI (strict + monitoring)
- [x] Relatório e baseline de acessibilidade (global e por rota)
- [ ] Cobertura E2E completa dos fluxos críticos

## Fase 2 (Dias 31-60) - Diferenciação
- [ ] Gateway de pagamentos (PIX/cartão) com callback/webhook
- [ ] Conciliação financeira automática
- [x] Ajuda contextual integrada (base documental + estrutura por tela)
- [ ] Ajuda contextual em todas as telas (UI final + busca integrada)
- [ ] Painel de retenção e engajamento
- [x] Métricas operacionais de auditoria (top ações, top atores, volume diário)

## Fase 3 (Dias 61-90) - Escala Premium
- [ ] Portal aluno mobile-first
- [ ] Permissões granulares por ação
- [ ] Observabilidade avançada (métricas, alertas e tracing)
- [ ] Staging + release process + rollback validado

## Sprint atual em execução
### Sprint 1 (concluída)
- Segurança: concluído
- CI/CD base: concluído
- Testes iniciais + one-click: concluído
- Auditoria de ações críticas: concluído
- Acessibilidade estruturante + gate CI: concluído

### Sprint 2 (em andamento)
- Cobertura de testes E2E prioritários: em andamento
- Ajuda contextual em UI completa: em andamento
- Base de métricas operacionais (auditoria/qualidade): concluído (auditoria)
