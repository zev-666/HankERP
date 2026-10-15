from fastapi import Request
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass


async def get_db(request: Request = None):
    """
    每個請求一個 session。

    v2.3.2：**這裡不再 commit。** FastAPI 0.135 的 yield 相依在回應送出
    之後才退棧，寫在 `yield` 之後的 commit 必然比 200 晚到，下一個請求就
    讀不到剛「成功」寫入的資料。commit 改由 app/db_commit_route.py 的
    CommitBeforeResponseRoute 在回應送出之前執行；這裡只負責把 session
    交給它（request.state.db），以及出錯時 rollback、最後關閉。
    """
    async with AsyncSessionLocal() as session:
        if request is not None:
            request.state.db = session
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
