FROM python:3.11-slim
WORKDIR /app
# PYTHONPATH=/app：確保 `python scripts/seed_data.py` 這類直接以檔案路徑執行的腳本
# 也能正確 import app 套件（python直接執行.py檔時，sys.path[0]會是該腳本自己所在的
# scripts/目錄，而不是WORKDIR，若不設定PYTHONPATH會出現ModuleNotFoundError: No module named 'app'）
ENV PYTHONPATH=/app
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
# 資安：升級pip本身至已修復已知CVE的版本（pip是建置工具，不隨應用程式運行，但升級成本為零）
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 資安：建立非root使用者執行容器，降低若容器被攻破時的影響範圍（容器逃逸風險降低）
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
