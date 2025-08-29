"""
應用程式主模組 - 使用 Gradio 實作 UI 介面
"""

import os
from dotenv import load_dotenv
import gradio as gr
from typing import List, Dict, Any

from src.text_splitter import TextSplitter
from src.embedding_provider import OpenAIEmbeddingProvider
from src.vector_database import VectorDatabase
from src.file_processor import FileProcessor

# 預設設定
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_TOP_K = 10
DEFAULT_MODEL = "text-embedding-3-small"


class MarkdownVectorApp:
    """
    Markdown 文件向量化應用程式
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        model_name: str = DEFAULT_MODEL,
        db_directory: str = "./chroma_db",
        collection_name: str = "markdown_documents",
        max_file_size_mb: float = 5.0,
        enable_markdown_cleaning: bool = True,
        cleaning_strategy: str = "balanced",
        preserve_code_blocks: bool = True,
        preserve_headings_as_context: bool = True,
    ):
        """
        初始化應用程式

        Args:
            chunk_size: 切分大小
            chunk_overlap: 切分重疊
            model_name: 嵌入模型名稱
            db_directory: 資料庫目錄
            collection_name: 集合名稱
            max_file_size_mb: 單一檔案大小上限 (MB)
            enable_markdown_cleaning: 是否啟用 Markdown 清理
            cleaning_strategy: 清理策略
            preserve_code_blocks: 是否保留代碼塊
            preserve_headings_as_context: 是否保留標題作為上下文
        """
        # 初始化元件
        self.text_splitter = TextSplitter(chunk_size, chunk_overlap)
        self.embedding_provider = OpenAIEmbeddingProvider(model_name)
        self.vector_db = VectorDatabase(db_directory, collection_name)
        self.file_processor = FileProcessor(
            max_file_size_mb=max_file_size_mb,
            enable_markdown_cleaning=enable_markdown_cleaning,
            cleaning_strategy=cleaning_strategy,
            preserve_code_blocks=preserve_code_blocks,
            preserve_headings_as_context=preserve_headings_as_context,
        )

    def process_files(
        self,
        files: List,
        chunk_size: int,
        chunk_overlap: int,
        enable_cleaning: bool = True,
        cleaning_strategy: str = "balanced",
        preserve_code: bool = True,
        preserve_headings: bool = True,
    ) -> Dict[str, Any]:
        """
        處理上傳的檔案

        Args:
            files: 上傳的檔案列表
            chunk_size: 切分大小
            chunk_overlap: 切分重疊
            enable_cleaning: 是否啟用 Markdown 清理
            cleaning_strategy: 清理策略
            preserve_code: 是否保留代碼塊
            preserve_headings: 是否保留標題

        Returns:
            Dict: 處理結果
        """
        if not files:
            return {"status": "error", "message": "未提供檔案", "ingested_files": []}

        # 更新切分器和文件處理器設定
        self.text_splitter = TextSplitter(chunk_size, chunk_overlap)

        # 為此次處理創建新的文件處理器
        temp_file_processor = FileProcessor(
            max_file_size_mb=self.file_processor.max_file_size_bytes / (1024 * 1024),
            enable_markdown_cleaning=enable_cleaning,
            cleaning_strategy=cleaning_strategy,
            preserve_code_blocks=preserve_code,
            preserve_headings_as_context=preserve_headings,
        )

        successful_files = []
        failed_files = []
        total_chunks = 0

        for file in files:
            # 獲取檔案資訊
            file_path = file.name
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)

            # 驗證檔案
            is_valid, error_msg = temp_file_processor.validate_file(
                file_path, file_size
            )
            if not is_valid:
                failed_files.append({"filename": file_name, "reason": error_msg})
                continue

            # 讀取檔案內容（包含 Markdown 清理）
            content = temp_file_processor.read_file_content(file_path)
            if content is None:
                failed_files.append(
                    {"filename": file_name, "reason": "無法讀取檔案內容"}
                )
                continue

            # 切分文件
            chunks = self.text_splitter.split_file(file_name, content)
            if not chunks:
                failed_files.append(
                    {"filename": file_name, "reason": "檔案內容為空或切分失敗"}
                )
                continue

            # 獲取文字列表進行嵌入
            texts = [chunk["text"] for chunk in chunks]

            try:
                # 產生嵌入
                embeddings = self.embedding_provider.embed_texts(texts)

                # 儲存到向量資料庫
                self.vector_db.add_documents(chunks, embeddings)

                successful_files.append(file_name)
                total_chunks += len(chunks)
            except Exception as e:
                failed_files.append(
                    {"filename": file_name, "reason": f"處理時發生錯誤: {str(e)}"}
                )

        return {
            "status": "success" if successful_files else "error",
            "message": f"成功處理 {len(successful_files)} 個檔案，總計 {total_chunks} 個片段",
            "ingested_files": successful_files,
            "failed_files": failed_files,
        }

    def search_documents(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        搜尋文件

        Args:
            query: 查詢文字
            top_k: 返回數量

        Returns:
            List[Dict]: 搜尋結果
        """
        if not query:
            return []

        try:
            # 產生查詢向量
            query_embedding = self.embedding_provider.embed_texts([query])[0]

            # 搜尋向量資料庫
            results = self.vector_db.search(query_embedding, top_k)

            # 格式化結果
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "score": f"{result['score']:.4f}",
                        "filename": result["metadata"]["source_filename"],
                        "chunk_index": result["metadata"]["chunk_index"],
                        "start": result["metadata"]["start"],
                        "end": result["metadata"]["end"],
                        "text": result["text"],
                    }
                )

            return formatted_results
        except Exception as e:
            print(f"搜尋時發生錯誤: {e}")
            return []

    def list_documents(self) -> List[str]:
        """
        列出已儲存的文件

        Returns:
            List[str]: 文件列表
        """
        return self.vector_db.list_documents()

    def delete_document(self, filename: str) -> Dict[str, Any]:
        """
        刪除文件

        Args:
            filename: 要刪除的文件名稱

        Returns:
            Dict: 處理結果
        """
        if not filename:
            return {"status": "error", "message": "未提供檔案名稱"}

        success = self.vector_db.delete_document(filename)

        if success:
            return {"status": "success", "message": f"成功刪除文件: {filename}"}
        else:
            return {"status": "error", "message": f"刪除文件時發生錯誤: {filename}"}

    def preview_markdown_cleaning(
        self,
        files: List,
        enable_cleaning: bool = True,
        cleaning_strategy: str = "balanced",
        preserve_code: bool = True,
        preserve_headings: bool = True,
    ) -> Dict[str, Any]:
        """
        預覽 Markdown 清理效果

        Args:
            files: 檔案列表
            enable_cleaning: 是否啟用清理
            cleaning_strategy: 清理策略
            preserve_code: 是否保留代碼塊
            preserve_headings: 是否保留標題

        Returns:
            Dict: 預覽結果
        """
        if not files:
            return {"status": "error", "message": "未提供檔案"}

        # 只預覽第一個檔案
        file = files[0]
        file_path = file.name
        file_name = os.path.basename(file_path)

        try:
            # 讀取原始內容
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            if enable_cleaning:
                # 創建臨時處理器
                temp_processor = FileProcessor(
                    enable_markdown_cleaning=True,
                    cleaning_strategy=cleaning_strategy,
                    preserve_code_blocks=preserve_code,
                    preserve_headings_as_context=preserve_headings,
                )

                # 獲取預覽
                preview_result = temp_processor.get_cleaning_preview(
                    original_content, max_length=800
                )
                preview_result["filename"] = file_name
                preview_result["cleaning_enabled"] = True

                return {
                    "status": "success",
                    "message": f"預覽檔案: {file_name}",
                    "preview": preview_result,
                }
            else:
                return {
                    "status": "success",
                    "message": f"預覽檔案: {file_name} (未啟用清理)",
                    "preview": {
                        "filename": file_name,
                        "cleaning_enabled": False,
                        "original_preview": original_content[:800]
                        + ("..." if len(original_content) > 800 else ""),
                        "cleaned_preview": "清理功能已停用",
                        "stats": {"message": "清理功能已停用"},
                    },
                }

        except Exception as e:
            return {"status": "error", "message": f"讀取檔案時發生錯誤: {str(e)}"}


def create_ui(app: MarkdownVectorApp):
    """
    建立 Gradio UI 介面

    Args:
        app: MarkdownVectorApp 實例
    """

    with gr.Blocks(
        title="Markdown 文件向量化服務",
        theme=gr.themes.Default(),
        analytics_enabled=False,
        mode="simple",
    ) as interface:
        gr.Markdown("# Markdown 文件向量化服務")
        gr.Markdown("上傳、向量化、搜尋 Markdown 文件")

        with gr.Tabs():
            # 上傳頁簽
            with gr.TabItem("上傳文件"):
                with gr.Row():
                    with gr.Column():
                        upload_files = gr.File(
                            label="上傳 Markdown 檔案",
                            file_types=[".md"],
                            file_count="multiple",
                        )
                        with gr.Row():
                            chunk_size = gr.Slider(
                                label="Chunk Size",
                                minimum=100,
                                maximum=2000,
                                value=DEFAULT_CHUNK_SIZE,
                                step=100,
                            )
                            chunk_overlap = gr.Slider(
                                label="Chunk Overlap",
                                minimum=0,
                                maximum=500,
                                value=DEFAULT_CHUNK_OVERLAP,
                                step=50,
                            )

                        # Markdown 預處理設定
                        with gr.Accordion("Markdown 預處理設定", open=False):
                            enable_cleaning = gr.Checkbox(
                                label="啟用 Markdown 格式清理",
                                value=True,
                                info="移除 Markdown 格式符號以提升檢索精度",
                            )
                            cleaning_strategy = gr.Dropdown(
                                label="清理策略",
                                choices=["conservative", "balanced", "aggressive"],
                                value="balanced",
                                info="保守型保留更多格式，積極型清理更徹底",
                            )
                            with gr.Row():
                                preserve_code = gr.Checkbox(
                                    label="保留代碼塊內容", value=True
                                )
                                preserve_headings = gr.Checkbox(
                                    label="保留標題作為上下文", value=True
                                )

                        upload_button = gr.Button("上傳並處理")
                        preview_button = gr.Button("預覽清理效果", variant="secondary")
                    with gr.Column():
                        upload_output = gr.JSON(label="處理結果")
                        preview_output = gr.JSON(label="清理預覽", visible=False)

                upload_button.click(
                    fn=app.process_files,
                    inputs=[
                        upload_files,
                        chunk_size,
                        chunk_overlap,
                        enable_cleaning,
                        cleaning_strategy,
                        preserve_code,
                        preserve_headings,
                    ],
                    outputs=upload_output,
                )

                # 預覽清理效果事件處理
                def handle_preview(
                    files,
                    enable_cleaning,
                    cleaning_strategy,
                    preserve_code,
                    preserve_headings,
                ):
                    result = app.preview_markdown_cleaning(
                        files,
                        enable_cleaning,
                        cleaning_strategy,
                        preserve_code,
                        preserve_headings,
                    )
                    return result, gr.update(visible=True)

                preview_button.click(
                    fn=handle_preview,
                    inputs=[
                        upload_files,
                        enable_cleaning,
                        cleaning_strategy,
                        preserve_code,
                        preserve_headings,
                    ],
                    outputs=[preview_output, preview_output],
                )

            # 搜尋頁簽
            with gr.TabItem("搜尋文件"):
                with gr.Row():
                    # 上半部：搜尋輸入區域
                    query_text = gr.Textbox(
                        label="輸入查詢文字",
                        placeholder="輸入要搜尋的文字...",
                        lines=3,
                        scale=3,
                    )

                    top_k = gr.Slider(
                        label="結果數量 (Top K)",
                        minimum=1,
                        maximum=20,
                        value=DEFAULT_TOP_K,
                        step=1,
                        container=True,
                        scale=1,
                    )
                with gr.Row():
                    search_button = gr.Button("搜尋", size="lg")
                    clean_button = gr.Button("清除", size="lg")

                with gr.Row():
                    # 下半部：搜尋結果區域
                    search_output = gr.Dataframe(
                        label="搜尋結果",
                        headers=[
                            "分數",
                            "檔案名稱",
                            "片段索引",
                            "開始位置",
                            "結束位置",
                            "文字內容",
                        ],
                        col_count=(6, "fixed"),
                        interactive=False,
                        column_widths=[
                            80,
                        ],  # 設定每欄寬度（單位：像素）
                    )

                # 將搜尋結果轉換為資料框格式
                def format_search_results(query, top_k):
                    results = app.search_documents(query, top_k)
                    if not results:
                        return []

                    # 轉換為列表格式
                    formatted_data = []
                    for result in results:
                        formatted_data.append(
                            [
                                result["score"],
                                result["filename"],
                                result["chunk_index"],
                                result["start"],
                                result["end"],
                                result["text"],
                            ]
                        )

                    return formatted_data

                search_button.click(
                    fn=format_search_results,
                    inputs=[query_text, top_k],
                    outputs=search_output,
                    api_name="search",
                )

                # 清除搜尋結果 callback
                def clear_search():
                    return "", []

                clean_button.click(
                    fn=clear_search,
                    inputs=None,
                    outputs=[query_text, search_output],
                )

            # 管理頁簽
            with gr.TabItem("文件管理"):
                with gr.Row():
                    with gr.Column():
                        refresh_button = gr.Button("重新整理文件列表")
                        document_list = gr.Dropdown(
                            label="選擇文件",
                            choices=[],
                            interactive=True,
                            allow_custom_value=True,
                        )
                        delete_button = gr.Button("刪除所選文件")
                    with gr.Column():
                        management_output = gr.JSON(label="操作結果")

                def reload_document_list():
                    """
                    更新文件列表
                    """
                    choices = app.list_documents()
                    return gr.Dropdown(
                        choices=choices, value=choices[0] if choices else None
                    )

                def delete_and_update(filename):
                    if not filename:
                        return {"status": "error", "message": "請選擇要刪除的文件"}, []
                    result = app.delete_document(filename)
                    choices = app.list_documents()
                    return result, gr.Dropdown(
                        choices=choices, value=choices[0] if choices else None
                    )

                # 初始化時載入文件列表
                interface.load(
                    fn=reload_document_list, inputs=None, outputs=document_list
                )

                # 重新整理文件列表
                refresh_button.click(
                    fn=reload_document_list,
                    inputs=None,
                    outputs=document_list,
                )

                # 刪除文件
                delete_button.click(
                    fn=delete_and_update,
                    inputs=[document_list],
                    outputs=[management_output, document_list],
                )

    return interface


def main():
    """
    主函數
    """
    # 載入 .env 設定（如果存在）
    load_dotenv()

    # 從環境變數讀取可覆寫的設定
    db_directory = os.getenv("CHROMA_DB_DIRECTORY", "./chroma_db")
    collection_name = os.getenv("COLLECTION_NAME", "markdown_documents")
    try:
        chunk_size = int(os.getenv("DEFAULT_CHUNK_SIZE", str(DEFAULT_CHUNK_SIZE)))
    except ValueError:
        chunk_size = DEFAULT_CHUNK_SIZE
    try:
        chunk_overlap = int(
            os.getenv("DEFAULT_CHUNK_OVERLAP", str(DEFAULT_CHUNK_OVERLAP))
        )
    except ValueError:
        chunk_overlap = DEFAULT_CHUNK_OVERLAP
    model_name = os.getenv("MODEL_NAME", DEFAULT_MODEL)
    try:
        max_file_size_mb = float(os.getenv("MAX_FILE_SIZE_MB", "5.0"))
    except ValueError:
        max_file_size_mb = 5.0

    # Markdown 預處理設定
    markdown_cleaning_enabled = os.getenv(
        "MARKDOWN_CLEANING_ENABLED", "true"
    ).lower() in ("true", "1", "yes")
    markdown_cleaning_strategy = os.getenv("MARKDOWN_CLEANING_STRATEGY", "balanced")
    preserve_code_blocks = os.getenv("PRESERVE_CODE_BLOCKS", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    preserve_headings_as_context = os.getenv(
        "PRESERVE_HEADINGS_AS_CONTEXT", "true"
    ).lower() in ("true", "1", "yes")

    # 如果 env 指向的資料庫目錄不存在或沒有 chroma 資料，fallback 到 ./chroma_db（專案內預設位置）
    chosen_db_directory = db_directory
    try:
        has_chroma_file = False
        if os.path.isdir(db_directory):
            # 檢查是否有 chroma.sqlite3 或任何檔案存在
            for fname in os.listdir(db_directory):
                if fname.endswith(".sqlite3") or fname.endswith(".db"):
                    has_chroma_file = True
                    break
    except Exception:
        has_chroma_file = False

    if not has_chroma_file:
        alt = "./chroma_db"
        if os.path.isdir(alt):
            chosen_db_directory = alt
            print(
                f"CHROMA_DB_DIRECTORY '{db_directory}' empty/missing — falling back to '{alt}'"
            )
        else:
            # 否則仍使用原本設定（資料夾會在 VectorDatabase 建構時建立）
            chosen_db_directory = db_directory

    # 初始化應用程式
    app = MarkdownVectorApp(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        model_name=model_name,
        db_directory=chosen_db_directory,
        collection_name=collection_name,
        max_file_size_mb=max_file_size_mb,
        enable_markdown_cleaning=markdown_cleaning_enabled,
        cleaning_strategy=markdown_cleaning_strategy,
        preserve_code_blocks=preserve_code_blocks,
        preserve_headings_as_context=preserve_headings_as_context,
    )

    # 由環境變數讀取 Gradio host/port
    host = os.getenv("GRADIO_SERVER_NAME", os.getenv("HOST", "127.0.0.1"))
    port_str = os.getenv("GRADIO_SERVER_PORT", os.getenv("PORT", "7860"))
    try:
        port = int(port_str)
    except (TypeError, ValueError):
        port = 7860

    # 顯示實際使用的設定（診斷用）
    print(
        f"Using config: CHROMA_DB_DIRECTORY={chosen_db_directory}, COLLECTION_NAME={collection_name}, "
        f"DEFAULT_CHUNK_SIZE={chunk_size}, DEFAULT_CHUNK_OVERLAP={chunk_overlap}, MODEL_NAME={model_name}, "
        f"MAX_FILE_SIZE_MB={max_file_size_mb}, MARKDOWN_CLEANING_ENABLED={markdown_cleaning_enabled}, "
        f"MARKDOWN_CLEANING_STRATEGY={markdown_cleaning_strategy}, "
        f"GRADIO_SERVER_NAME={host}, GRADIO_SERVER_PORT={port_str}"
    )

    # print(f"伺服器啟動: http://{host}:{port}")

    # 建立 UI
    interface = create_ui(app)

    # 啟動伺服器（server_name 為 host，server_port 為整數 port）
    interface.launch(
        show_error=True, server_name=host, server_port=port, share=False, debug=True
    )


if __name__ == "__main__":
    main()
