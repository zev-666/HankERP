"""
docker-compose.offline.yml 的守門測試（v2.3.11，離線版）。

離線版也是獨立 compose 檔，會跟開發版漂移。檢查：
1. 安全前提：只有 frontend 開 port 且預設綁 127.0.0.1；backend／db／redis 不開 port；
   不信任任何「來源 IP」標頭（沒有 Cloudflare）；沒有需要網路的 cloudflared。
2. 同源 API 的三個設定一起出現（少一個，登入就會打到錯的網址）。
3. 開發版有的服務與環境變數，離線版也有。
"""
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "docker-compose.yml"
OFF = ROOT / "docker-compose.offline.yml"

if not (DEV.exists() and OFF.exists()):
    pytest.skip("compose 檔在 repo 根目錄，此執行環境看不到（例如 backend 容器內）",
                allow_module_level=True)

doc = yaml.safe_load(OFF.read_text(encoding="utf-8"))
off = doc["services"]
dev = yaml.safe_load(DEV.read_text(encoding="utf-8"))["services"]


def _env(svc: dict) -> dict:
    env = svc.get("environment") or {}
    if isinstance(env, list):
        env = dict(e.split("=", 1) if "=" in e else (e, None) for e in env)
    return env


def _cmd(svc: dict) -> str:
    c = svc.get("command") or ""
    return " ".join(c) if isinstance(c, list) else str(c)


def test_only_frontend_publishes_a_port_and_defaults_to_this_computer():
    exposed = {n: s["ports"] for n, s in off.items() if s.get("ports")}
    assert list(exposed) == ["frontend"], "離線版只有 frontend 可以開 port"
    assert exposed["frontend"] == ["${ERP_BIND:-127.0.0.1}:${ERP_PORT:-3000}:3000"], \
        "預設只綁 127.0.0.1；開放區域網路要使用者明確執行 LAN-On"


def test_backend_is_private_and_login_limit_is_shared_lan_friendly():
    env = _env(off["backend"])
    assert str(env["TRUST_CF_CONNECTING_IP"]).lower() == "false", "離線版沒有 Cloudflare，不可信任它的標頭"
    # 全廠共用一個計數器（見 compose 檔第 4 點）：要比正式站的 5 寬，但不能沒有上限
    count, per = env["LOGIN_RATE_LIMIT"].split("/")
    assert per == "minute" and 10 <= int(count) <= 60
    assert env["ENVIRONMENT"] == "production"
    assert not off["backend"].get("ports")


def test_same_origin_api_settings_come_together():
    fe = off["frontend"]
    args = fe["build"]["args"]
    assert args["NEXT_PUBLIC_API_URL"] == "same-origin"
    assert args["API_PROXY_TARGET"] == "http://backend:8000"
    assert _env(fe)["INTERNAL_API_URL"] == "http://backend:8000"
    assert _env(fe)["API_PROXY_TARGET"] == "http://backend:8000"


def test_no_service_needs_the_internet_and_no_dev_shortcuts():
    assert "cloudflared" not in off
    for name, s in off.items():
        for v in s.get("volumes") or []:
            src = v.split(":", 1)[0] if isinstance(v, str) else v.get("source", "")
            assert src not in ("./backend", "./frontend"), f"{name} 掛載了原始碼 {src}"
        assert "--reload" not in _cmd(s), f"{name} 用了 --reload"
        assert s.get("restart") == "unless-stopped", f"{name} 重開機後不會自己起來"


def test_secrets_are_required_not_defaulted():
    text = OFF.read_text(encoding="utf-8")
    assert "erp_pass_2025" not in text, "離線版不可沿用公開在 GitHub 上的預設資料庫密碼"
    assert "${DB_PASSWORD:?" in text and "${SECRET_KEY:?" in text and "${SEED_ADMIN_PASSWORD:?" in text


def test_project_name_and_image_names_are_fixed():
    assert doc["name"] == "everevo-offline", "固定專案名稱：資料與開發版分開"
    assert off["backend"]["image"] == off["celery"]["image"] == "everevo-erp-backend:offline"
    assert off["frontend"]["image"] == "everevo-erp-frontend:offline"


def test_offline_has_every_dev_service_and_env_key():
    for name, s in dev.items():
        assert name in off, f"開發版有服務 {name}，離線版沒有"
        missing = set(_env(s)) - set(_env(off[name]))
        assert not missing, f"{name} 的環境變數 {sorted(missing)} 離線版沒有"
    dev_args = set(dev["frontend"]["build"].get("args") or {})
    assert dev_args <= set(off["frontend"]["build"]["args"])
