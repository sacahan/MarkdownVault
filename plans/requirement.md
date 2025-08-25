---
post_title: "Markdown 文件向量化服務 MVP 規格"
author1: "Brian Han"
post_slug: "markdown-vector-mvp"
microsoft_alias: "your_alias"
featured_image: "/images/featured-image.jpg"
categories: ["AI", "文件管理"]
tags: ["Markdown", "向量化", "Chroma", "Gradio"]
ai_note: true
summary: "將 Markdown 文件轉為向量並儲存於本地 Chroma 向量資料庫的 MVP 規格"
post_date: "2025-08-24"
---

# Markdown 文件向量化服務 MVP 規格

## 簡介

本文件說明如何將單一 Markdown 檔案轉為向量，並儲存在本地向量資料庫（Chroma），以支援
語意搜尋與基本管理功能。

## 核心 MVP 功能

以下為 MVP 的核心功能與行為定義。

### 文件處理

- 支援單一或多筆 Markdown 檔案上傳。
- 執行基本格式與大小驗證。
- 透過 Gradio UI 進行文件上傳。

### 文件切分

- 使用以字元為基礎的切分策略。
- 預設參數：chunk_size = 1000，overlap = 200。

### 向量化

- 使用預設嵌入模型 `text-embedding-3-small`。
- 儲存向量時，metadata 包含來源檔名、位置與原始片段。

### 向量儲存

- 使用 Chroma 作為本地向量資料庫，提供儲存與索引功能。

### 檢索

- 提供語意搜尋功能，支援 `top_k`（預設 k = 5）。
- 使用 Gradio UI 進行文件檢索。

### 管理

- 列出已儲存的文件集合。
- 刪除指定文件以及對應的向量資料。

### 預設設定

| 參數       | 預設值                 |
| ---------- | --------------------- |
| chunk_size | 1000                  |
| overlap    | 200                   |
| model      | text-embedding-3-small|
| vector_db  | chroma                |
| top_k      | 5                     |

### 注意事項

此為 MVP，僅聚焦核心功能；生產化需求（如完整權限管理、監控或分散式儲存）不在本階段範疇。

### 程式流程範例

```yaml
# 上傳 -> 驗證 -> 切分 -> 向量化 -> 儲存 -> 檢索
```
