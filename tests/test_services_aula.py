from app.schemas.tenant import AulaCreate, InscricaoCreate
from app.services import aula as aula_service
from app.models.tenant import DiaSemana, InscricaoStatus


def test_criar_aula(db_session, seed_tenant):
    aula = aula_service.criar_aula(
        AulaCreate(
            nome="Spinning",
            professor_id=seed_tenant["admin"].id,
            dia_semana=DiaSemana.segunda,
            horario_inicio="08:00",
            horario_fim="09:00",
            capacidade_maxima=1,
        ),
        db_session,
    )
    assert aula.id is not None
    assert aula.nome == "Spinning"


def test_inscricao_lista_espera(db_session, seed_tenant):
    aula = aula_service.criar_aula(
        AulaCreate(
            nome="Yoga",
            professor_id=seed_tenant["admin"].id,
            dia_semana=DiaSemana.terca,
            horario_inicio="10:00",
            horario_fim="11:00",
            capacidade_maxima=1,
        ),
        db_session,
    )
    al2 = seed_tenant["aluno"]
    from app.models.tenant import Aluno
    al3 = Aluno(nome="Aluno 2", email="aluno2@fit.com", ativo=True)
    db_session.add(al3)
    db_session.commit()

    i1 = aula_service.inscrever_aluno(InscricaoCreate(aluno_id=al2.id, aula_id=aula.id), db_session)
    i2 = aula_service.inscrever_aluno(InscricaoCreate(aluno_id=al3.id, aula_id=aula.id), db_session)
    assert i1.status == InscricaoStatus.confirmada
    assert i2.status == InscricaoStatus.lista_espera
