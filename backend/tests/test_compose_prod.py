"""
docker-compose.prod.yml 的守門測試（v2.3.5）。

正式環境 compose 是獨立檔案（Compose 的 override 無法可靠移除 ports），
所以它會跟開發版 docker-compose.yml 漂移。這裡檢查兩件事：
1. 正式版的安全前提沒被改掉：不開任何 port、不掛原始碼、不用 --reload、
   限流信任 CF-Connecting-IP 的前提（沒有 port 對外）成立、cloudflared 版本固定。
2. 開發版新增的服務、環境變數、前端建置參數，正式版也有（防止只改一邊）。

兩個 compose 檔在 repo 根目錄；在 backend 容器裡（只掛 backend/）讀不到時會 skip，
CI（整個 repo checkout）一定會跑。
"""
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "docker-compose.yml"
PROD = ROOT / "docker-compose.prod.yml"

if not (DEV.exists() and PROD.exists()):
    pytest.skip("compose 檔在 repo 根目錄，此執行環境看不到（例如 backend 容器內）",
                allow_module_level=True)


def _load(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))["services"]


def _env(svc: dict) -> dict:
    env = svc.get("environment") or {}
    if isinstance(env, list):
        env = dict(e.split("=", 1) if "=" in e else (e, None) for e in env)
    return env


def _cmd(svc: dict) -> str:
    c = svc.get("command") or ""
    return " ".join(c) if isinstance(c, list) else str(c)


dev, prod = _load(DEV), _load(PROD)


def test_prod_exposes_no_ports():
    exposed = {name: s["ports"] for name, s in prod.items() if s.get("ports")}
    assert exposed == {}, "正式版不可對外開 port（流量只走 Cloudflare Tunnel；Docker port 會繞過 ufw）"


def test_prod_does_not_mount_source_or_reload():
    for name, s in prod.items():
        for v in s.get("volumes") or []:
            src = v.split(":", 1)[0] if isinstance(v, str) else v.get("source", "")
            assert src not in ("./backend", "./frontend"), f"{name} 掛載了原始碼 {src}"
        assert "--reload" not in _cmd(s), f"{name} 用了 --reload"


def test_prod_backend_trusts_cloudflare_only_because_no_ports():
    env = _env(prod["backend"])
    assert str(env["TRUST_CF_CONNECTING_IP"]).lower() == "true"
    assert env["ENVIRONMENT"] == "production"
    assert not prod["backend"].get("ports")


def test_cloudflared_present_and_pinned():
    cf = prod["cloudflared"]
    image = cf["image"]
    assert image.startswith("cloudflare/cloudflared:")
    assert not image.endswith(":latest"), "cloudflared 要固定版號，避免主機重建時默默升級"
    assert "TUNNEL_TOKEN" in _env(cf)


def test_prod_has_every_dev_service_and_env_key():
    for name, s in dev.items():
        assert name in prod, f"開發版有服務 {name}，正式版沒有"
        missing = set(_env(s)) - set(_env(prod[name]))
        assert not missing, f"{name} 的環境變數 {sorted(missing)} 正式版沒有"


def test_frontend_build_args_in_sync():
    dev_args = set((dev["frontend"]["build"].get("args") or {}))
    prod_args = set((prod["frontend"]["build"].get("args") or {}))
    assert "NEXT_PUBLIC_SITE_URL" in dev_args, "sitemap/robots 的網址是建置期寫死的，開發版也要傳"
    assert dev_args <= prod_args
