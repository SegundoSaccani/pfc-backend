from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


class _FakeSessionOk:
    def execute(self, *_args, **_kwargs):
        return None


class _FakeSessionDown:
    def execute(self, *_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def _override_ok():
    yield _FakeSessionOk()


def _override_down():
    yield _FakeSessionDown()


def test_health_ok(client):
    app.dependency_overrides[get_db] = _override_ok
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


def test_health_db_unreachable(client):
    app.dependency_overrides[get_db] = _override_down
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json() == {"status": "error", "db": "unreachable"}
