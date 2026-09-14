from celery import Celery
from app.config import settings

celery_app = Celery(
    "acrylic_erp",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=True,
    task_track_started=True,
    # 明確設定，避免Celery 6.0起broker_connection_retry預設行為變更時靜默改變啟動重試邏輯
    # （目前版本會顯示CPendingDeprecationWarning提醒此設定，明確指定可消除警告並future-proof）
    broker_connection_retry_on_startup=True,
)

# ⚠️ 修正：autodiscover_tasks(["app.tasks"]) 慣例上會去找 app.tasks.tasks 這個子模組
# （Django風格的app/tasks.py命名慣例），但本專案的task檔案叫nesting_tasks.py，
# 命名不符合這個慣例，導致autodiscover完全找不到任何task —— worker啟動後
# 收到.delay()送來的任務會回報NotRegistered錯誤，永遠執行不了。
# 改用明確import，不依賴autodiscover的命名慣例，確保task一定會被註冊。
from app.tasks import nesting_tasks  # noqa: E402,F401 — 確保task被celery_app註冊
