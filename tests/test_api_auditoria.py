from datetime import datetime

from fastapi.testclient import TestClient

from app.core.deps import require_superadmin
from app.db.database import get_db
from main import app


class FakeAuditLog:
    def __init__(self, idx: int):
        self.id = idx
        self.actor_id = str(idx % 3)
        self.actor_scope = "public"
        self.actor_role = "superadmin"
        self.action = "criar_academia" if idx % 2 == 0 else "editar_academia"
        self.resource_type = "academia"
        self.resource_id = str(idx)
        self.schema_name = None
        self.details = None
        self.ip = "127.0.0.1"
        self.criado_em = datetime.utcnow()


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self._offset = 0
        self._limit = None
        self._entity_marker = ""

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def with_entities(self, *args, **_kwargs):
        self._entity_marker = " ".join(str(a) for a in args)
        return self

    def group_by(self, *_args, **_kwargs):
        return self

    def offset(self, value):
        self._offset = value
        return self

    def limit(self, value):
        self._limit = value
        return self

    def all(self):
        # Retornos agregados usados pelas métricas
        marker = self._entity_marker.lower()
        if "action" in marker:
            return [("criar_academia", 40), ("editar_academia", 20)]
        if "actor_id" in marker:
            return [("1", 30), ("2", 15)]
        if "date(" in marker or " as dia" in marker or "dia" in marker:
            return [("2026-01-01", 10), ("2026-01-02", 8)]

        data = self.data[self._offset :]
        if self._limit is not None:
            data = data[: self._limit]
        return data

    def count(self):
        return len(self.data)


class FakeSession:
    def __init__(self):
        self.data = [FakeAuditLog(i) for i in range(120)]

    def query(self, *_args, **_kwargs):
        return FakeQuery(self.data)


def _override_db():
    yield FakeSession()


def _override_superadmin():
    return {"id": 1, "role": "superadmin"}


def test_api_auditoria_ok():
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_superadmin] = _override_superadmin
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/superadmin/auditoria?limit=25&offset=10")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 25
        assert "action" in data[0]
    finally:
        app.dependency_overrides.clear()


def test_api_auditoria_com_filtros_periodo_ordem():
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_superadmin] = _override_superadmin
    try:
        client = TestClient(app)
        resp = client.get(
            "/api/v1/superadmin/auditoria?acao=criar&actor_id=1&data_inicio=2026-01-01&data_fim=2026-12-31&ordem=asc&limit=10&offset=0"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 10
    finally:
        app.dependency_overrides.clear()


def test_api_auditoria_metricas_ok():
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_superadmin] = _override_superadmin
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/superadmin/auditoria/metricas?data_inicio=2026-01-01&data_fim=2026-12-31")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_eventos" in data
        assert "top_acoes" in data
        assert "top_atores" in data
        assert "volume_diario" in data
    finally:
        app.dependency_overrides.clear()
