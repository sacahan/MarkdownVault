# Markdown 文件向量化服務

這是一個 MVP 實作，用於將 Markdown 文件轉換為向量並儲存於本地 Chroma 向量資料庫，以支援語意搜尋與基本管理功能。

## 功能

- 支援單一或多筆 Markdown 檔案上傳
- 基本格式與大小驗證
- 以字元為基礎的文件切分
- 使用 OpenAI 的 `text-embedding-3-small` 模型進行向量化
- 儲存向量至本地 Chroma 資料庫
- 提供語意搜尋功能
- 提供基本檔案管理功能（列出、刪除）

## 安裝與環境設定

### 前置需求

- Python 3.10+
- OpenAI API 金鑰

### 安裝步驟

1. 複製或下載本專案

2. 安裝依賴套件

```bash
pip install -e .
```

對於開發環境，請安裝開發依賴：

```bash
pip install -e ".[dev]"
```

1. 設定環境變數

建立 `.env` 檔案並新增以下內容：

```plaintext
OPENAI_API_KEY=your_api_key_here
```

## 使用方式

1. 啟動應用程式

```bash
python app.py
```

1. 開啟瀏覽器前往 `http://localhost:7860` 使用 Gradio 介面

### 上傳文件

- 在「上傳文件」頁籤選擇一個或多個 Markdown 檔案
- 調整切分參數（如有需要）
- 點擊「上傳並處理」按鈕

### 搜尋文件

- 在「搜尋文件」頁籤輸入查詢文字
- 調整回傳結果數量（如有需要）
- 點擊「搜尋」按鈕查看結果

### 管理文件

- 在「文件管理」頁籤查看已儲存的文件
- 選擇文件進行刪除

## 預設設定

| 參數       | 預設值                  |
|------------|------------------------|
| chunk_size | 1000                   |
| overlap    | 200                    |
| model      | text-embedding-3-small |
| top_k      | 5                      |

## 專案結構

```text
.
├── app.py                # 主應用程式與 Gradio UI
├── pyproject.toml      # 相依套件與專案設定
├── src/
│   ├── __init__.py
│   ├── text_splitter.py  # 文件切分器
│   ├── embedding_provider.py  # 嵌入模型提供者
│   ├── vector_database.py  # 向量資料庫管理
│   └── file_processor.py  # 檔案處理
├── tests.py              # 單元測試
└── .env                  # 環境變數 (需自行建立)
```

## 執行測試

```bash
pytest
```

## 注意事項

- 此為 MVP 實作，未包含完整的錯誤處理與優化
- 預設使用本地硬碟儲存向量資料，長期使用建議設定備份機制
