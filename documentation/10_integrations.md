# Integrações

- SMTP para envio de e-mail (recuperação e notificações)
- APScheduler para execução diária de tarefas

## Falhas esperadas
- SMTP indisponível: envio retorna `False`; notificação pode ir para `falha`
- Scheduler ausente em ambiente de teste: aplicação deve continuar operando
