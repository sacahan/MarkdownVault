"""
應用程式主模組 - 使用 Gradio 實作 UI 介面
"""

import os
from dotenv import load_dotenv
import gradio as gr
from typing import List, Dict, Any

from src.text_splitter import TextSplitter
from src.embedding_provider import (
    OpenAIEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
)
from src.vector_database import VectorDatabase
from src.file_processor import FileProcessor

# 預設設定
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_TOP_K = 10

# 模型設定
AVAILABLE_MODELS = {
    "OpenAI (text-embedding-3-small)": "openai",
    "Local (all-MiniLM-L6-v2)": "minilm",
}
DEFAULT_MODEL_KEY = "OpenAI (text-embedding-3-small)"


class MarkdownVectorApp:
    """
    Markdown 文件向量化應用程式
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        db_directory: str = "./chroma_db",
        base_collection_name: str = "markdown_documents",
        max_file_size_mb: float = 5.0,
        enable_markdown_cleaning: bool = True,
        cleaning_strategy: str = "balanced",
        preserve_code_blocks: bool = True,
        preserve_headings_as_context: bool = True,
    ):
        """
        初始化應用程式
        """
        self.text_splitter = TextSplitter(chunk_size, chunk_overlap)
        self.file_processor_config = {
            "max_file_size_mb": max_file_size_mb,
            "enable_markdown_cleaning": enable_markdown_cleaning,
            "cleaning_strategy": cleaning_strategy,
            "preserve_code_blocks": preserve_code_blocks,
            "preserve_headings_as_context": preserve_headings_as_context,
        }

        # 初始化所有可用的嵌入提供者
        self.embedding_providers = {
            "openai": OpenAIEmbeddingProvider(model_name="text-embedding-3-small"),
            "minilm": SentenceTransformerEmbeddingProvider(
                model_name="all-MiniLM-L6-v2"
            ),
        }

        # 為每個模型建立獨立的向量資料庫實例
        self.vector_dbs = {
            model_id: VectorDatabase(db_directory, f"{base_collection_name}_{model_id}")
            for model_id in AVAILABLE_MODELS.values()
        }

    def _get_provider_and_db(self, model_key: str) -> tuple:
        model_id = AVAILABLE_MODELS.get(model_key, "openai")
        provider = self.embedding_providers[model_id]
        db = self.vector_dbs[model_id]
        return provider, db

    def process_files(
        self,
        files: List,
        chunk_size: int,
        chunk_overlap: int,
        model_key: str,
        enable_cleaning: bool = True,
        cleaning_strategy: str = "balanced",
        preserve_code: bool = True,
        preserve_headings: bool = True,
    ) -> Dict[str, Any]:
        if not files:
            return {"status": "error", "message": "未提供檔案", "ingested_files": []}

        embedding_provider, vector_db = self._get_provider_and_db(model_key)

        self.text_splitter = TextSplitter(chunk_size, chunk_overlap)
        temp_file_processor = FileProcessor(
            max_file_size_mb=self.file_processor_config["max_file_size_mb"],
            enable_markdown_cleaning=enable_cleaning,
            cleaning_strategy=cleaning_strategy,
            preserve_code_blocks=preserve_code,
            preserve_headings_as_context=preserve_headings,
        )

        successful_files, failed_files, total_chunks = [], [], 0

        for file in files:
            file_path, file_name = file.name, os.path.basename(file.name)
            file_size = os.path.getsize(file_path)

            is_valid, error_msg = temp_file_processor.validate_file(
                file_path, file_size
            )
            if not is_valid:
                failed_files.append({"filename": file_name, "reason": error_msg})
                continue

            content = temp_file_processor.read_file_content(file_path)
            if content is None:
                failed_files.append(
                    {"filename": file_name, "reason": "無法讀取檔案內容"}
                )
                continue

            chunks = self.text_splitter.split_file(file_name, content)
            if not chunks:
                failed_files.append(
                    {"filename": file_name, "reason": "檔案內容為空或切分失敗"}
                )
                continue

            texts = [chunk["text"] for chunk in chunks]

            try:
                embeddings = embedding_provider.embed_texts(texts)
                vector_db.add_documents(chunks, embeddings)
                successful_files.append(file_name)
                total_chunks += len(chunks)
            except Exception as e:
                failed_files.append(
                    {"filename": file_name, "reason": f"處理時發生錯誤: {str(e)}"}
                )

        return {
            "status": "success" if successful_files else "error",
            "message": f"成功處理 {len(successful_files)} 個檔案至 Collection: {vector_db.collection.name}",
            "ingested_files": successful_files,
            "failed_files": failed_files,
        }

    def search_documents(
        self, query: str, top_k: int, model_key: str
    ) -> List[Dict[str, Any]]:
        if not query:
            return []

        embedding_provider, vector_db = self._get_provider_and_db(model_key)

        try:
            query_embedding = embedding_provider.embed_texts([query])[0]
            results = vector_db.search(query_embedding, top_k)
            return [
                {
                    "score": f"{result['score']:.4f}",
                    "filename": result["metadata"]["source_filename"],
                    "chunk_index": result["metadata"]["chunk_index"],
                    "start": result["metadata"]["start"],
                    "end": result["metadata"]["end"],
                    "text": result["text"],
                }
                for result in results
            ]
        except Exception as e:
            print(f"搜尋時發生錯誤: {e}")
            return []

    def list_documents(self, model_key: str) -> List[str]:
        _, vector_db = self._get_provider_and_db(model_key)
        return vector_db.list_documents()

    def delete_document(self, filename: str, model_key: str) -> Dict[str, Any]:
        if not filename:
            return {"status": "error", "message": "未提供檔案名稱"}

        _, vector_db = self._get_provider_and_db(model_key)
        success = vector_db.delete_document(filename)

        if success:
            return {
                "status": "success",
                "message": f"已從 Collection '{vector_db.collection.name}' 刪除文件: {filename}",
            }
        else:
            return {
                "status": "error",
                "message": f"從 Collection '{vector_db.collection.name}' 刪除文件時發生錯誤: {filename}",
            }

    def preview_markdown_cleaning(self, files: List, *args) -> Dict[str, Any]:
        # Unpack args for clarity
        (enable_cleaning, cleaning_strategy, preserve_code, preserve_headings) = args
        if not files:
            return {"status": "error", "message": "未提供檔案"}

        file = files[0]
        try:
            with open(file.name, "r", encoding="utf-8") as f:
                original_content = f.read()

            if enable_cleaning:
                temp_processor = FileProcessor(
                    enable_markdown_cleaning=True,
                    cleaning_strategy=cleaning_strategy,
                    preserve_code_blocks=preserve_code,
                    preserve_headings_as_context=preserve_headings,
                )
                preview_result = temp_processor.get_cleaning_preview(original_content)
                preview_result["filename"] = os.path.basename(file.name)
                return {"status": "success", "preview": preview_result}
            else:
                return {
                    "status": "success",
                    "preview": {
                        "original_preview": original_content[:800],
                        "cleaned_preview": "清理功能已停用",
                        "stats": {"message": "清理功能已停用"},
                    },
                }
        except Exception as e:
            return {"status": "error", "message": f"讀取檔案時發生錯誤: {str(e)}"}


def create_ui(app: MarkdownVectorApp):
    with gr.Blocks(
        title="Markdown 文件向量化服務", theme=gr.themes.Default()
    ) as interface:
        gr.Markdown("# Markdown 文件向量化服務")

        # Helper function to get collection name markdown
        def get_collection_name_md(model_key: str):
            model_id = AVAILABLE_MODELS.get(model_key, "openai")
            collection_name = app.vector_dbs[model_id].collection.name
            return f"**當前資料庫 (Collection):** `{collection_name}`"

        with gr.Tabs():
            with gr.TabItem("上傳文件"):
                with gr.Row():
                    with gr.Column():
                        model_choice_upload = gr.Dropdown(
                            label="選擇嵌入模型",
                            choices=list(AVAILABLE_MODELS.keys()),
                            value=DEFAULT_MODEL_KEY,
                        )
                        collection_display_upload = gr.Markdown(
                            get_collection_name_md(DEFAULT_MODEL_KEY)
                        )
                        upload_files = gr.File(
                            label="上傳 Markdown 檔案",
                            file_types=[".md"],
                            file_count="multiple",
                        )
                        with gr.Row():
                            chunk_size = gr.Slider(
                                label="Chunk Size",
                                value=DEFAULT_CHUNK_SIZE,
                                minimum=100,
                                maximum=2000,
                                step=100,
                            )
                            chunk_overlap = gr.Slider(
                                label="Chunk Overlap",
                                value=DEFAULT_CHUNK_OVERLAP,
                                minimum=0,
                                maximum=500,
                                step=50,
                            )
                        with gr.Accordion("Markdown 預處理設定", open=False):
                            enable_cleaning = gr.Checkbox(
                                label="啟用 Markdown 格式清理", value=True
                            )
                            cleaning_strategy = gr.Dropdown(
                                label="清理策略",
                                choices=["conservative", "balanced", "aggressive"],
                                value="balanced",
                            )
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

                model_choice_upload.change(
                    fn=get_collection_name_md,
                    inputs=model_choice_upload,
                    outputs=collection_display_upload,
                )

                upload_button.click(
                    fn=app.process_files,
                    inputs=[
                        upload_files,
                        chunk_size,
                        chunk_overlap,
                        model_choice_upload,
                        enable_cleaning,
                        cleaning_strategy,
                        preserve_code,
                        preserve_headings,
                    ],
                    outputs=upload_output,
                )

                def handle_preview(files, *args):
                    result = app.preview_markdown_cleaning(files, *args)
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

            with gr.TabItem("搜尋文件"):
                model_choice_search = gr.Dropdown(
                    label="選擇搜尋模型 (需與文件所用模型對應)",
                    choices=list(AVAILABLE_MODELS.keys()),
                    value=DEFAULT_MODEL_KEY,
                )
                collection_display_search = gr.Markdown(
                    get_collection_name_md(DEFAULT_MODEL_KEY)
                )
                with gr.Row():
                    query_text = gr.Textbox(label="輸入查詢文字", lines=3, scale=3)
                    top_k = gr.Slider(
                        label="結果數量 (Top K)",
                        value=DEFAULT_TOP_K,
                        minimum=1,
                        maximum=20,
                        step=1,
                        scale=1,
                    )
                gr.Examples(
                    examples=[
                        "介紹一下自己",
                        "你的學經歷？",
                        "你擅長的技術？",
                        "偏好的工作類型？",
                        "如何聯絡你？",
                    ],
                    inputs=query_text,
                    label="常用搜尋語句範例",
                )
                search_button = gr.Button("搜尋")
                search_output = gr.Dataframe(
                    label="搜尋結果",
                    headers=["score", "filename", "text"],
                    col_count=(3, "fixed"),
                )

                model_choice_search.change(
                    fn=get_collection_name_md,
                    inputs=model_choice_search,
                    outputs=collection_display_search,
                )

                def format_search_results(query, top_k, model_key):
                    results = app.search_documents(query, top_k, model_key)
                    return [[r["score"], r["filename"], r["text"]] for r in results]

                search_button.click(
                    fn=format_search_results,
                    inputs=[query_text, top_k, model_choice_search],
                    outputs=search_output,
                )

            with gr.TabItem("文件管理"):
                model_choice_manage = gr.Dropdown(
                    label="選擇模型對應的資料庫",
                    choices=list(AVAILABLE_MODELS.keys()),
                    value=DEFAULT_MODEL_KEY,
                )
                collection_display_manage = gr.Markdown(
                    get_collection_name_md(DEFAULT_MODEL_KEY)
                )
                with gr.Row():
                    with gr.Column():
                        refresh_button = gr.Button("重新整理文件列表")
                        document_list = gr.Dropdown(
                            label="選擇文件", choices=[], interactive=True
                        )
                        delete_button = gr.Button("刪除所選文件")
                    with gr.Column():
                        management_output = gr.JSON(label="操作結果")

                def reload_document_list(model_key):
                    choices = app.list_documents(model_key)
                    return gr.Dropdown(
                        choices=choices, value=choices[0] if choices else None
                    )

                def delete_and_update(filename, model_key):
                    if not filename:
                        return {
                            "status": "error",
                            "message": "請選擇要刪除的文件",
                        }, gr.update()
                    result = app.delete_document(filename, model_key)
                    choices = app.list_documents(model_key)
                    return result, gr.Dropdown(
                        choices=choices, value=choices[0] if choices else None
                    )

                model_choice_manage.change(
                    fn=lambda k: (get_collection_name_md(k), reload_document_list(k)),
                    inputs=model_choice_manage,
                    outputs=[collection_display_manage, document_list],
                )
                refresh_button.click(
                    fn=reload_document_list,
                    inputs=model_choice_manage,
                    outputs=document_list,
                )
                delete_button.click(
                    fn=delete_and_update,
                    inputs=[document_list, model_choice_manage],
                    outputs=[management_output, document_list],
                )

    return interface


def main():
    load_dotenv()
    db_directory = os.getenv("CHROMA_DB_DIRECTORY", "./chroma_db")
    collection_name = os.getenv("COLLECTION_NAME", "markdown_documents")
    # ... (rest of the main function remains largely the same)
    app = MarkdownVectorApp(
        db_directory=db_directory,
        base_collection_name=collection_name,
        # other params from env or defaults
    )
    interface = create_ui(app)
    host = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    interface.launch(server_name=host, server_port=port, share=False, debug=True)


if __name__ == "__main__":
    # A simplified main for brevity in this example
    load_dotenv()
    app = MarkdownVectorApp(
        db_directory=os.getenv("CHROMA_DB_DIRECTORY", "./chroma_db"),
        base_collection_name=os.getenv("COLLECTION_NAME", "markdown_documents"),
    )
    ui = create_ui(app)
    ui.launch(server_name="127.0.0.1", server_port=7861, share=False, debug=True)
