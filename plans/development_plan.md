---
post_title: "Markdown 文件向量化服務 開發計劃 (MVP)"
author1: "Brian Han"
post_slug: "markdown-vector-devplan"
microsoft_alias: "your_alias"
featured_image: "/images/featured-image.jpg"
categories: ["AI", "文件管理"]
tags: ["Markdown", "向量化", "Chroma", "Gradio", "MVP"]
ai_note: true
summary: "將 `requirement.md` 的 MVP 規格拆成可執行的開發計劃、里程碑、驗收標準與風險緩解措施。"
post_date: "2025-08-25"
---

# 開發計劃 — Markdown 文件向量化服務 (MVP)

本文件根據 `plans/requirement.md` 中的 MVP 規格，將需求拆解為可交付的開發任務、時程、驗收準則與測試策略，供實作團隊使用。

## 一行摘要

把單一或多筆 Markdown 檔案上傳、切分、向量化並儲存在本地 Chroma，提供 Gradio UI 的上傳、搜尋與管理介面，聚焦於核心功能與快速可驗證交付。

## 需求抽取與 checklist

以下為從 `requirement.md` 明確抽出的需求項目（每項會對應任務與驗收標準）：

- [x] 支援單一或多筆 Markdown 檔案上傳（Gradio）
- [x] 基本格式與大小驗證（檔案類型、大小上限）
- [x] 以字元為基礎的切分器（chunk_size=1000, overlap=200）
- [x] 使用 `text-embedding-3-small` 嵌入模型進行向量化
- [x] 儲存向量至本地 Chroma，metadata 含來源檔名、位置與原始片段
- [x] 提供語意搜尋（top_k，預設 5）與 Gradio 檢索介面
- [x] 管理功能：列出文件集合、刪除指定文件與對應向量
- [x] 預設設定可被修改（chunk_size、overlap、model、top_k）

## 假設（若未指定則採用）

- 開發環境為 macOS；以 Python 為主要實作語言，使用 `gradio`, `chromadb`, `openai` 或等價的 embedding 客戶端。
- Chroma 使用本地目錄儲存（非遠端服務）。
- 預期 MVP 不處理權限、驗證、併發或分散式部署（留給未來迭代）。

## 技術棧（建議）

- 語言：Python 3.10+
- Web UI：Gradio
- 向量資料庫：Chroma (local)
- 嵌入模型：OpenAI `text-embedding-3-small` 或可本地替代的 embedding provider
- 依賴管理：`requirements.txt` 或 `pyproject.toml`

## 主要里程碑與時程建議（短期 MVP，建議 2 週衝刺）

1. 初始化與環境建置 (1 天)
   - 建立專案結構、虛擬環境、依賴檔
2. 檔案上傳與驗證（Gradio） (2 天)
   - 實作上傳表單、處理單檔/多檔、檔案類型/大小驗證
3. 切分模組 (1 天)
   - 實作字元切分器，參數化 chunk_size、overlap
4. 嵌入與 Chroma 儲存 (2 天)
   - 呼叫 embedding API，寫入 Chroma，metadata 寫入來源資訊
5. 檢索與 UI (2 天)
   - 實作語意搜尋 API、Gradio 的查詢介面、top_k 設定
6. 管理功能與刪除 (1 天)
   - 列表、刪除文件與向量
7. 測試、品質閘門與發佈 (1-2 天)
   - 單元測試、整合測試、簡易 README 與使用示例

總計：約 9-11 個工作天（含緩衝）。

## 低階任務清單（實作導向）

1. 建立專案骨幹
   - `src/`、`app.py`（或 `main.py`）、`requirements.txt`、`README.md`
2. 上傳端點
   - Gradio UI：檔案上傳欄、參數輸入（chunk_size、overlap）
   - 驗證：允許 `.md`，大小限制（例如 5MB/檔）
3. 切分器（module）
   - 公開函式：split_text(text, chunk_size=1000, overlap=200) -> list[dict]{text, start, end}
4. 嵌入器（module）
   - 包裝 embedding client：embed_texts(list[str]) -> list[vectors]
5. 向量儲存（module）
   - 初始化 Chroma local collection
   - 插入向量並寫 metadata: {source_filename, chunk_index, start, end, original_text}
6. 檢索 API 與 UI
   - query -> embeddings -> chroma.search(top_k)
   - 回傳原始片段與來源資訊
7. 管理功能
   - list_collections/list_documents
   - delete_document(collection_id or source_filename)
8. 設定管理
   - config 檔或環境變數覆蓋（例如 `.env`）
9. 測試
   - 單元：切分器、嵌入器（mock）、Chroma CRUD
   - 集成：上傳到檢索端到端流程

## 最小 API / 合約 (2-4 bullets)

- 上傳 API (Gradio button): inputs = files[], chunk_size:int, overlap:int -> outputs = {ingested_files: [filename], status}
- 檢索 API: inputs = query:str, top_k:int -> outputs = [{score, source_filename, chunk_index, snippet}]
- 管理 API: list_documents() -> [filenames]; delete_document(filename) -> success:boolean

## 驗收標準（Acceptance Criteria）

- 能上傳一或多個 `.md`，且檔案通過驗證後被切分並成功寫入 Chroma
- 查詢文字能回傳與 query 相關的 top_k 片段，且每筆結果含來源檔名與片段位置
- 能列出已存文件並刪除指定文件與其向量

## 邊界與風險（與緩解）

- 大型檔案（>5MB）：拒絕或分批上傳；在 UI 顯示明確錯誤訊息
- 嵌入服務連線失敗：實作重試機制與友善錯誤回饋，測試 offline mock
- Chroma 資料損壞：在開發階段採用備份目錄；在 production 增加備援

## 測試策略（快速）

- 單元測試：切分器行為（短/剛好等邊界）、metadata 正確性
- 模擬測試：mock embedding 回傳固定向量，測試 Chroma 寫入與檢索
- E2E：上傳一個示例 `.md`，執行查詢並驗證回傳結果包含預期片段

## 品質閘門（Quality gates）

- Build: `pip install -r requirements.txt` 成功
- Lint/Typecheck: 基本 flake8/black（可選）無阻斷錯誤
- Tests: 單元/整合測試通過（最低 3 個測項）

## 交付物

- `src/`：程式碼（上傳、切分、嵌入、儲存、檢索、管理）
- `requirements.txt` 或 `pyproject.toml`
- `README.md`：如何跑起來、範例流程
- 測試檔案（pytest）

## 下一步（立即可執行）

1. 建立 repo 基礎檔案與虛擬環境；把技術棧與時程分享給團隊
2. 開始第 1 日的環境建置任務，並在完成後提交初步 PR（包含 `requirements.txt` 與 `app.py` skeleton）

---

以上為根據 `requirement.md` 產出的開發計劃草案，若要我直接在專案中建立專案骨幹（`src/`、`requirements.txt`、範例 `app.py`、簡易 Gradio 起始頁），我可以接著建立最小可運行範例。請告訴我是否要繼續實作。
