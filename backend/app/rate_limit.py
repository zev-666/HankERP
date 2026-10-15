"""
全域共用的 Rate Limiter 實例。

⚠️ 設計說明：main.py 與各模組router若各自呼叫 Limiter() 建立獨立實例，
   會導致 @limiter.limit() 裝飾器用來計數的實例，跟 app.state.limiter
   （slowapi例外處理常式讀取Retry-After等標頭時使用的實例）不是同一個物件。
   雖然基本計數行為仍可能正常運作（因為各自實例的計數本身是自洽的），
   但這是脆弱且不符合slowapi建議用法的架構，全專案應共用這裡定義的單一實例，
   避免main.py與auth/router.py分別建立造成不一致。
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def client_ip(request: Request) -> str:
    """
    限流用的「訪客 IP」。

    上 Cloudflare Tunnel（v2.3.5）後，每個請求都從同一個 cloudflared 容器進來，
    request.client.host 全部相同——直接用它，全站會共用一個計數器
    （任何人登入失敗 5 次，所有人被鎖；官網詢價全網每小時只能 5 筆）。
    真實訪客 IP 由 Cloudflare 放在 CF-Connecting-IP 標頭。

    只有 TRUST_CF_CONNECTING_IP=true 才信任這個標頭：後端若能被直接連到
    （本機開發、或正式站還開著 :8000），任何人都能偽造它來繞過限流。
    正式站的 docker-compose.prod.yml 不對外開任何 port，所有流量必經 Cloudflare，才打開。
    設定在呼叫時才讀，測試可直接改 settings。
    """
    if settings.TRUST_CF_CONNECTING_IP:
        cf_ip = request.headers.get("cf-connecting-ip", "").strip()
        if cf_ip:
            return cf_ip
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip)
