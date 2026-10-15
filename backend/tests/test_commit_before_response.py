"""
「回 2xx 時資料已經 commit」的驗證（v2.3.2）。

背景見 app/db_commit_route.py。這支測試不需要資料庫：用一個會記錄事件的
假 session 取代 AsyncSessionLocal，再包一層 ASGI 記錄「回應開始送出」的
時間點，直接比較 commit 和回應的先後。

1. test_fastapi_runs_yield_teardown_after_response
   特性測試：證明 FastAPI 0.135 的 yield 相依收尾在回應送出之後。
   這是 bug 的根因。哪天升級 FastAPI 改了這個行為，這支會先失敗，
   提醒我們重新檢視 db_commit_route 是否還需要。

2. test_commit_happens_before_response_is_sent
   用真正的 get_db＋CommitBeforeResponseRoute，commit 必須早於回應。
   用舊版 get_db（commit 寫在 yield 之後）跑這支會失敗——已在 v2.3.2
   開發時實際驗證過。

3. test_no_commit_when_handler_raises／test_no_commit_on_error_response
   端點 raise 或回 4xx 時不得 commit。

4. test_every_api_route_commits_before_response
   守門：app 上每一支 /api/ 路由都必須是 CommitBeforeResponseRoute。
   新模組忘記在 APIRouter 加 route_class，這裡會失敗，而不是上線後
   默默讓寫入晚到。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, FastAPI, HTTPException  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.database as database  # noqa: E402
from app.db_commit_route import CommitBeforeResponseRoute  # noqa: E402


class FakeSession:
    """只記錄事件的假 session，介面對齊 get_db／路由會用到的部分。"""

    def __init__(self, events: list):
        self.events = events
        self._tx = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def in_transaction(self) -> bool:
        return self._tx

    def add(self, obj) -> None:
        self._tx = True
        self.events.append("write")

    async def commit(self) -> None:
        self.events.append("commit")
        self._tx = False

    async def rollback(self) -> None:
        self.events.append("rollback")
        self._tx = False

    async def close(self) -> None:
        self.events.append("close")


def _recording(asgi_app, events: list):
    """包一層 ASGI，記下 http.response.start（回應開始送出）的時間點。"""
    async def app(scope, receive, send):
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                events.append("response-sent")
            await send(message)
        await asgi_app(scope, receive, send_wrapper)
    return app


def _build(route_class, db_dependency):
    router = APIRouter(route_class=route_class)

    @router.post("/write")
    async def write(db=Depends(db_dependency)):
        db.add(object())
        return {"ok": True}

    @router.post("/raise")
    async def raise_(db=Depends(db_dependency)):
        db.add(object())
        raise HTTPException(400, "nope")

    @router.post("/error-response")
    async def error_response(db=Depends(db_dependency)):
        db.add(object())
        return JSONResponse({"ok": False}, status_code=409)

    app = FastAPI()
    app.include_router(router)
    return app


def _client(monkeypatch, route_class, db_dependency=None):
    events: list = []
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: FakeSession(events))
    app = _build(route_class, db_dependency or database.get_db)
    return TestClient(_recording(app, events), raise_server_exceptions=False), events


# ── 1. 根因的特性測試 ─────────────────────────────────────────────────
def test_fastapi_runs_yield_teardown_after_response(monkeypatch):
    async def legacy_get_db():
        """v2.3 以前的 get_db 寫法：commit 寫在 yield 之後。"""
        async with database.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    client, events = _client(monkeypatch, APIRoute, legacy_get_db)
    assert client.post("/write").status_code == 200
    assert events.index("response-sent") < events.index("commit"), (
        "FastAPI 的 yield 收尾時機和 v2.3.2 開發時量到的不同了，"
        f"請重新檢視 app/db_commit_route.py 是否仍需要：{events}"
    )


# ── 2. 修正後：commit 必須早於回應 ─────────────────────────────────────
def test_commit_happens_before_response_is_sent(monkeypatch):
    client, events = _client(monkeypatch, CommitBeforeResponseRoute)
    assert client.post("/write").status_code == 200
    assert "commit" in events, events
    assert events.index("commit") < events.index("response-sent"), events
    assert events.count("commit") == 1, events


# ── 3. 失敗時不得 commit ──────────────────────────────────────────────
def test_no_commit_when_handler_raises(monkeypatch):
    client, events = _client(monkeypatch, CommitBeforeResponseRoute)
    assert client.post("/raise").status_code == 400
    assert "commit" not in events, events
    assert "rollback" in events, events


def test_no_commit_on_error_response(monkeypatch):
    client, events = _client(monkeypatch, CommitBeforeResponseRoute)
    assert client.post("/error-response").status_code == 409
    assert "commit" not in events, events
    assert "rollback" in events, events


# ── 4. 守門：每一支 /api/ 路由都要套上 ─────────────────────────────────
def test_every_api_route_commits_before_response():
    from app.main import app

    api_routes = [r for r in app.routes if isinstance(r, APIRoute) and r.path.startswith("/api/")]
    assert len(api_routes) > 60, f"路由數異常少（{len(api_routes)}），檢查 app.main 是否完整載入"
    missing = sorted(
        f"{','.join(sorted(r.methods))} {r.path}"
        for r in api_routes
        if not isinstance(r, CommitBeforeResponseRoute)
    )
    assert not missing, (
        "以下路由沒有使用 CommitBeforeResponseRoute，寫入會在回應之後才 commit。"
        "請在該模組的 APIRouter(...) 加上 route_class=CommitBeforeResponseRoute：\n  "
        + "\n  ".join(missing)
    )
