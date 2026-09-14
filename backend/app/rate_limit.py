"""
全域共用的 Rate Limiter 實例。

⚠️ 設計說明：main.py 與各模組router若各自呼叫 Limiter() 建立獨立實例，
   會導致 @limiter.limit() 裝飾器用來計數的實例，跟 app.state.limiter
   （slowapi例外處理常式讀取Retry-After等標頭時使用的實例）不是同一個物件。
   雖然基本計數行為仍可能正常運作（因為各自實例的計數本身是自洽的），
   但這是脆弱且不符合slowapi建議用法的架構，全專案應共用這裡定義的單一實例，
   避免main.py與auth/router.py分別建立造成不一致。
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
