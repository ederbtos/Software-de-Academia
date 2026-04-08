"""
Funções utilitárias de notificação.
Envia por e-mail via SMTP. Pode ser substituído por SMS/WhatsApp.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.models.tenant import (
    Notificacao, NotificacaoTipo, NotificacaoStatus,
    Aluno, Matricula, MatriculaStatus, Pagamento, PagamentoStatus,
)


def _smtp_config() -> dict:
    from app.core.config import get_settings
    s = get_settings()
    return {"host": s.smtp_host, "port": s.smtp_port, "user": s.smtp_user, "password": s.smtp_pass, "from_addr": s.smtp_from or s.smtp_user}


def enviar_email(destinatario: str, assunto: str, corpo: str) -> bool:
    """Envia e-mail via SMTP com as configurações do .env."""
    cfg = _smtp_config()
    if not cfg["host"] or not cfg["user"]:
        return False  # SMTP não configurado

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = cfg["from_addr"]
    msg["To"] = destinatario
    msg.attach(MIMEText(corpo, "html"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from_addr"], destinatario, msg.as_string())
        return True
    except Exception:
        return False


def gerar_notificacoes_vencimento(db: Session, dias_antecedencia: int = 5):
    """Cria notificações para alunos com mensalidade vencendo em até X dias."""
    from datetime import timedelta
    hoje = date.today()
    limite = hoje + timedelta(days=dias_antecedencia)

    pagamentos = (
        db.query(Pagamento)
        .filter(
            Pagamento.status == PagamentoStatus.pendente,
            Pagamento.data_vencimento <= limite,
            Pagamento.data_vencimento >= hoje,
        )
        .all()
    )

    for pag in pagamentos:
        matricula = db.query(Matricula).filter(Matricula.id == pag.matricula_id).first()
        if not matricula:
            continue

        existente = db.query(Notificacao).filter(
            Notificacao.aluno_id == matricula.aluno_id,
            Notificacao.tipo == NotificacaoTipo.vencimento_plano,
            Notificacao.status == NotificacaoStatus.pendente,
        ).first()
        if existente:
            continue

        aluno = db.query(Aluno).filter(Aluno.id == matricula.aluno_id).first()
        if not aluno:
            continue

        db.add(Notificacao(
            aluno_id=matricula.aluno_id,
            tipo=NotificacaoTipo.vencimento_plano,
            titulo="Mensalidade próxima do vencimento",
            mensagem=(
                f"Olá {aluno.nome}, sua mensalidade vence em "
                f"{pag.data_vencimento.strftime('%d/%m/%Y')}. "
                f"Valor: R$ {pag.valor:.2f}."
            ),
            status=NotificacaoStatus.pendente,
        ))
    db.commit()


def gerar_notificacoes_inadimplentes(db: Session):
    """Cria notificações para alunos com pagamentos já vencidos (inadimplentes)."""
    hoje = date.today()

    pagamentos_atrasados = (
        db.query(Pagamento)
        .filter(
            Pagamento.status == PagamentoStatus.pendente,
            Pagamento.data_vencimento < hoje,
        )
        .all()
    )

    for pag in pagamentos_atrasados:
        matricula = db.query(Matricula).filter(Matricula.id == pag.matricula_id).first()
        if not matricula:
            continue

        existente = db.query(Notificacao).filter(
            Notificacao.aluno_id == matricula.aluno_id,
            Notificacao.tipo == NotificacaoTipo.mensalidade_atrasada,
            Notificacao.status == NotificacaoStatus.pendente,
        ).first()
        if existente:
            continue

        aluno = db.query(Aluno).filter(Aluno.id == matricula.aluno_id).first()
        if not aluno:
            continue

        dias_atraso = (hoje - pag.data_vencimento).days
        db.add(Notificacao(
            aluno_id=matricula.aluno_id,
            tipo=NotificacaoTipo.mensalidade_atrasada,
            titulo="Mensalidade em atraso",
            mensagem=(
                f"Olá {aluno.nome}, sua mensalidade está em atraso há "
                f"{dias_atraso} dia(s). Vencimento: {pag.data_vencimento.strftime('%d/%m/%Y')}. "
                f"Valor: R$ {pag.valor:.2f}. Entre em contato para regularizar."
            ),
            status=NotificacaoStatus.pendente,
        ))
    db.commit()


def processar_notificacoes_pendentes(db: Session):
    """Envia as notificações pendentes por e-mail e atualiza o status."""
    pendentes = db.query(Notificacao).filter(Notificacao.status == NotificacaoStatus.pendente).all()

    for notif in pendentes:
        if notif.aluno_id:
            aluno = db.query(Aluno).filter(Aluno.id == notif.aluno_id).first()
            if aluno and aluno.email:
                sucesso = enviar_email(aluno.email, notif.titulo, notif.mensagem)
                notif.status = NotificacaoStatus.enviada if sucesso else NotificacaoStatus.falha
                notif.enviado_em = datetime.utcnow()

    db.commit()

