# Fluxos de Usuário

## Primeiros passos
1. Superadmin cria academia
2. (Opcional) cria admin da academia
3. Admin acessa e configura planos/funcionários
4. Cadastro de alunos
5. Matrícula e cobrança

## Fluxo financeiro
```mermaid
flowchart TD
  A[Aluno cadastrado] --> B[Matrícula]
  B --> C[Pagamento pendente]
  C -->|Pagar| D[Pago]
  C -->|Vence| E[Inadimplente]
```

## Fluxo treino
```mermaid
flowchart TD
  A[Aluno] --> B[Avaliação]
  B --> C[Criar treino]
  C --> D[Acompanhar check-ins]
```
