"""
Funções utilitárias de notificação.
Atualmente envia por e-mail via SMTP. Pode ser substituído por SMS/WhatsApp.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from sqlalchemy.orm import Session
from app.models.tenant import Notificacao, NotificacaoTipo, NotificacaoStatus, Aluno, Matricula, MatriculaStatus, Pagamento, PagamentoStatus


def enviar_email(destinatario: str, assunto: str, corpo: str, smtp_host: str = None, smtp_port: int = 587, smtp_user: str = None, smtp_pass: str = None):
    """Envia e-mail via SMTP. Configuração via variáveis de ambiente."""
    import os
    host = smtp_host or os.getenv("SMTP_HOST", "")
    port = smtp_port or int(os.getenv("SMTP_PORT", 587))
    user = smtp_user or os.getenv("SMTP_USER", "")
    password = smtp_pass or os.getenv("SMTP_PASS", "")

    if not host or not user:
        return False  # SMTP não configurado

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = user
    msg["To"] = destinatario
    msg.attach(MIMEText(corpo, "html"))

    try:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()
            server.login(user, password)
            server.sendmail(user, destinatario, msg.as_string())
        return True
    except Exception:
        return False


def gerar_notificacoes_vencimento(db: Session, dias_antecedencia: int = 5):
    """Cria notificações para alunos com mensalidade vencendo em X dias."""
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

        # Evita duplicidade
        existente = db.query(Notificacao).filter(
            Notificacao.aluno_id == matricula.aluno_id,
            Notificacao.tipo == NotificacaoTipo.vencimento_plano,
            Notificacao.status == NotificacaoStatus.pendente,
        ).first()
        if existente:
            continue

        aluno = db.query(Aluno).filter(Aluno.id == matricula.aluno_id).first()
        notif = Notificacao(
            aluno_id=matricula.aluno_id,
            tipo=NotificacaoTipo.vencimento_plano,
            titulo="Mensalidade próxima do vencimento",
            mensagem=f"Olá {aluno.nome}, sua mensalidade vence em {pag.data_vencimento.strftime('%d/%m/%Y')}. Valor: R$ {pag.valor}.",
            status=NotificacaoStatus.pendente,
        )
        db.add(notif)

    db.commit()


def processar_notificacoes_pendentes(db: Session):
    """Envia as notificações pendentes por e-mail."""
    from datetime import datetime
    pendentes = db.query(Notificacao).filter(Notificacao.status == NotificacaoStatus.pendente).all()

    for notif in pendentes:
        if notif.aluno_id:
            aluno = db.query(Aluno).filter(Aluno.id == notif.aluno_id).first()
            if aluno and aluno.email:
                sucesso = enviar_email(aluno.email, notif.titulo, notif.mensagem)
                notif.status = NotificacaoStatus.enviada if sucesso else NotificacaoStatus.falha
                notif.enviado_em = datetime.utcnow()

    db.commit()
