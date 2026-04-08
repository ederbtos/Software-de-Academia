"""
Agendador de tarefas periódicas usando APScheduler.
Executa verificações automáticas:
- Atualiza matrículas vencidas
- Gera notificações de vencimento próximo
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


def _get_all_schemas():
    from app.db.database import get_db
    from app.models.public import Academia, AcademiaStatus
    db = next(get_db())
    try:
        return [a.schema_name for a in db.query(Academia).filter(Academia.status == AcademiaStatus.ativa).all()]
    finally:
        db.close()


def _tarefa_vencimentos():
    from app.db.database import get_tenant_db
    from app.services.aluno import atualizar_status_matriculas
    from app.services.notificacao import (
        gerar_notificacoes_vencimento,
        gerar_notificacoes_inadimplentes,
        processar_notificacoes_pendentes,
    )
    for schema in _get_all_schemas():
        db = next(get_tenant_db(schema))
        try:
            atualizar_status_matriculas(db)
            gerar_notificacoes_vencimento(db)
            gerar_notificacoes_inadimplentes(db)
            processar_notificacoes_pendentes(db)
        finally:
            db.close()


def criar_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    # Roda todo dia às 07:00
    scheduler.add_job(_tarefa_vencimentos, CronTrigger(hour=7, minute=0), id="vencimentos_diario")
    return scheduler
