# Banco de Dados

## Modelagem

### Schema public
- `academias`
- `usuarios`
- `planos_globais`
- `password_reset_tokens`

### Schema tenant
- `funcionarios`, `planos`, `alunos`
- `matriculas`, `pagamentos`
- `presencas`, `avaliacoes_fisicas`
- `exercicios`, `treinos`, `treino_exercicios`
- `aulas`, `inscricoes_aulas`
- `notificacoes`

```mermaid
erDiagram
  ALUNO ||--o{ MATRICULA : possui
  PLANO ||--o{ MATRICULA : referencia
  MATRICULA ||--o{ PAGAMENTO : gera
  ALUNO ||--o{ PRESENCA : registra
  ALUNO ||--o{ AVALIACAO_FISICA : possui
  ALUNO ||--o{ TREINO : recebe
  TREINO ||--o{ TREINO_EXERCICIO : contem
  EXERCICIO ||--o{ TREINO_EXERCICIO : referencia
  AULA ||--o{ INSCRICAO_AULA : recebe
  ALUNO ||--o{ INSCRICAO_AULA : realiza
```
