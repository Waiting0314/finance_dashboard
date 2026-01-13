# 股票分析平台 MVP

這是一個基於 Django 開發的股票分析平台最小可行性產品 (MVP)。

## 功能特色

*   **使用者系統**: 支援使用者註冊、登入、登出及 Email 驗證。
*   **個人化儀表板**: 使用者登入後，可以看到專屬的儀表板。
*   **股票追蹤清單**: 使用者可以新增或移除股票到自己的追蹤清單。
*   **互動式圖表**: 使用 [ECharts](https://echarts.apache.org/) 繪製 K 線圖，並包含 MA5, MA10, MA20 等技術指標。
*   **背景任務**: 使用 `django-background-tasks` 抓取 Yahoo Finance 真實股價資料。

## 技術棧

*   **後端**: Django
*   **資料庫**: PostgreSQL (Docker 環境) / SQLite (本地開發)
*   **前端圖表**: ECharts
*   **背景任務**: `django-background-tasks`
*   **股價資料來源**: `yfinance`

## 使用 Docker 快速部署 (推薦)

本專案支援使用 Docker Compose 進行一鍵部署，包含 Django Web 服務、PostgreSQL 資料庫以及背景任務處理器。

### 1. 啟動服務

在專案根目錄下執行：

```bash
docker compose up --build
```

這將會啟動三個容器：
1. `db`: PostgreSQL 資料庫 (port 5432)
2. `web`: Django 應用程式 (port 8000)
3. `worker`: 背景任務處理器

### 2. 初始化資料庫

首次啟動時，需要進行資料庫遷移：

```bash
docker compose exec web python manage.py migrate
```

### 3. 建立管理者帳號 (可選)

```bash
docker compose exec web python manage.py createsuperuser
```

### 4. 訪問網站

開啟瀏覽器，訪問 `http://127.0.0.1:8000/`。

---

## 本地開發 (不使用 Docker)

### 1. 環境設定

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 初始化資料庫

```bash
python manage.py migrate
```

### 3. 啟動服務

需分別啟動 Web 伺服器與任務處理器：

**終端機 1:**
```bash
python manage.py runserver
```

**終端機 2:**
```bash
python manage.py process_tasks
```

## 驗證檔案

專案根目錄下包含 `verification_dashboard.html`，這是透過程式自動生成的儀表板 HTML 範例，可用於驗證前端 ECharts 資料引用是否正確。
