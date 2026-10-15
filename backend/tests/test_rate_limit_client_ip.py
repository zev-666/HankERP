"""
限流必須以「真實訪客 IP」計數（v2.3.5，上線 Cloudflare Tunnel）。

舊行為：key_func=get_remote_address，取 request.client.host。
上 Cloudflare Tunnel 後，所有請求都從同一個 cloudflared 容器進來，client.host 全部相同，
全站變成共用一個計數器：任何一個人登入失敗 5 次，所有人都被鎖 1 分鐘；
官網詢價（5/hour）變成全網每小時只能送 5 筆。

新行為：TRUST_CF_CONNECTING_IP=true 時改用 Cloudflare 帶來的 CF-Connecting-IP；
預設 false（不信任），因為後端若能被直接連到，攻擊者可以偽造這個標頭來繞過限流。

不需要資料庫：用專案共用的 limiter 掛一個最小 app，走 slowapi 的真實計數路徑。
已在 v2.3.4 舊程式上確認會失敗。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from app.config import settings  # noqa: E402
from app.rate_limit import limiter  # noqa: E402


def _client(name: str) -> TestClient:
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    async def endpoint(request: Request):
        return {"ok": True}

    endpoint.__name__ = name  # slowapi 以端點名稱區分計數，每個測試用不同名稱
    app.get("/t")(limiter.limit("2/minute")(endpoint))
    limiter.reset()
    return TestClient(app)


@pytest.fixture
def trust_cf(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_CF_CONNECTING_IP", True)


@pytest.fixture
def no_trust_cf(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_CF_CONNECTING_IP", False)


def test_different_visitors_behind_tunnel_have_separate_limits(trust_cf):
    """三個不同訪客各打一次，都不該被別人的次數連累（舊程式第三個就 429）。"""
    c = _client("rl_separate")
    codes = [c.get("/t", headers={"CF-Connecting-IP": ip}).status_code
             for ip in ("203.0.113.1", "203.0.113.2", "203.0.113.3")]
    assert codes == [200, 200, 200]


def test_same_visitor_behind_tunnel_is_still_limited(trust_cf):
    """同一個訪客超過次數仍要 429——修正不能變成完全不限流。"""
    c = _client("rl_same")
    h = {"CF-Connecting-IP": "203.0.113.9"}
    codes = [c.get("/t", headers=h).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_header_ignored_when_not_trusted(no_trust_cf):
    """預設不信任：直接連後端的人換 CF-Connecting-IP 也繞不過限流。"""
    c = _client("rl_spoof")
    codes = [c.get("/t", headers={"CF-Connecting-IP": f"198.51.100.{i}"}).status_code
             for i in range(3)]
    assert codes == [200, 200, 429]


def test_blank_header_falls_back_to_socket_address(trust_cf):
    """標頭空白時退回連線來源位址，不可讓所有空標頭的請求變成同一個 "" 以外的怪值。"""
    c = _client("rl_blank")
    codes = [c.get("/t", headers={"CF-Connecting-IP": "  "}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_setting_defaults_to_not_trusted():
    from app.config import Settings
    assert Settings.model_fields["TRUST_CF_CONNECTING_IP"].default is False
