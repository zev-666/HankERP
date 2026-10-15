"""
讓每個 API 請求在「回應送出之前」commit（v2.3.2）。

為什麼需要它
------------
FastAPI 0.135 的 `yield` 相依，是在 HTTP 回應**送出之後**才退棧的
（fastapi/routing.py 的 request_response：`await response(...)` 在
`request_stack` 的 async with 裡面，request_stack 結束才跑相依的收尾）。

舊的 get_db 把 `await session.commit()` 寫在 `yield` 之後，結果是：

    端點 flush → 回 200 給前端 → 才開始 commit

只要下一個請求貼得夠近（前端連續操作、CI、整合腳本），就會讀不到
上一個請求「已經回報成功」的資料。2026-10-15 本機實測：連續 200 輪
建料→建產品→建 BOM，195 輪失敗；請求間隔拉到 300ms 則 30/30 通過；
失敗輪次的資料事後查資料庫全部都在（200/200），證明是 commit 晚到，
不是資料遺失。

作法
----
路由處理函式在 FastAPI 的 `function_stack` 裡執行，它比 `request_stack`
早退、而且一定在 `await response(...)` 之前。所以在處理函式拿到 Response
之後、回傳之前 commit，就保證「回 2xx 的時候資料已經落庫」。

- 回應狀態碼 < 400 → commit
- 回應狀態碼 >= 400（端點自己回錯誤，沒有 raise）→ rollback
- 端點 raise（HTTPException 或其他例外）→ 不會走到這裡，由 get_db 的
  except 分支 rollback
- commit 本身失敗（例如外鍵、唯一鍵衝突）→ 例外往外拋，前端拿到 500，
  而不是先拿到 200 再默默失敗

使用方式
--------
每個 `APIRouter(...)` 都要帶 `route_class=CommitBeforeResponseRoute`。
`include_router` 會保留來源 router 的 route class（routing.py
`route_class_override=type(route)`），所以只設 app.router 沒有用。
tests/test_commit_before_response.py 會檢查每一支 /api/ 路由都有套上，
新模組忘記加會在 CI 失敗，不會變成默默掉資料。
"""
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.routing import APIRoute


class CommitBeforeResponseRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        handler = super().get_route_handler()

        async def commit_before_response(request: Request) -> Response:
            response = await handler(request)
            session = getattr(request.state, "db", None)
            if session is not None and session.in_transaction():
                if response.status_code < 400:
                    await session.commit()
                else:
                    await session.rollback()
            return response

        return commit_before_response
