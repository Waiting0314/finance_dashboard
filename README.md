# 股票分析平台 MVP

這是一個基於 Django 開發的股票分析平台最小可行性產品 (MVP)。

## 功能特色

*   **使用者系統**: 支援使用者註冊、登入、登出及 Email 驗證。
*   **個人化儀表板**: 使用者登入後，可以看到專屬的儀表板。
*   **股票追蹤清單**: 使用者可以新增或移除股票到自己的追蹤清單。
*   **互動式圖表**: 使用 [ECharts](https://echarts.apache.org/) 繪製 K 線圖，並包含 MA5, MA10, MA20 等技術指標。
*   **背景任務**: 使用 `django-background-tasks` 建立了一個用於抓取股價資料的背景任務框架。

**注意**: 由於開發環境的限制，前端圖表目前使用動態產生的**假資料**進行展示，而股價抓取功能僅完成程式碼開發，未在整合環境中進行完整驗證。

## 技術棧

*   **後端**: Django
*   **資料庫**: SQLite
*   **前端圖表**: ECharts
*   **背景任務**: `django-background-tasks`
*   **股價資料來源 (開發中)**: `yfinance`

## 安裝與啟動步驟

### 1. 環境設定

建議使用 Python 虛擬環境。

```bash
# 建立虛擬環境
python -m venv venv

# 啟用虛擬環境 (macOS / Linux)
source venv/bin/activate

# 啟用虛擬環境 (Windows)
# venv\Scripts\activate
```

### 2. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 3. 初始化資料庫

這將會建立一個名為 `db.sqlite3` 的資料庫檔案，並建立所有需要的資料表。

```bash
python manage.py migrate
```

### 4. 建立管理者帳號 (可選)

您可以建立一個超級使用者，以便登入後台管理介面。

```bash
python manage.py createsuperuser
```

### 5. 啟動服務

您需要啟動兩個服務：Django 開發伺服器和背景任務處理器。請分別在兩個不同的終端機 (Terminal) 中執行以下指令。

**終端機 1: 啟動 Django 網站伺服器**

```bash
python manage.py runserver
```

網站將會在 `http://127.0.0.1:8000/` 上運行。

**終端機 2: 啟動背景任務處理器**

這個服務負責執行如抓取股價等耗時的背景任務。

```bash
python manage.py process_tasks
```

### 6. 使用方式

1.  開啟瀏覽器，訪問 `http://127.0.0.1:8000/`。
2.  註冊一個新帳號。
3.  檢查您執行 `runserver` 的終端機，您會看到一封模擬的啟用信件內容，其中包含一個啟用連結。
4.  複製並在瀏覽器中訪問該啟用連結，以啟用您的帳號。
5.  使用您剛才註冊的帳號登入。
6.  在儀表板中，嘗試新增一筆股票代號 (例如 `2330.TW` 或 `AAPL`) 到您的追蹤清單，您將會看到圖表出現。