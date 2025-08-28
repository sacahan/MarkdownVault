# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Environment

```bash
# Install dependencies
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Start application (recommended method)
./scripts/start.sh

# Start application directly
python app.py

# Using uv (if available)
uv run app.py
```

### Testing commands

```bash
# Run unit tests
pytest

# Run specific test files
pytest tests/tests.py
pytest tests/integration_tests.py
```

### Code Quality

```bash
# Format code (if black is installed)
black .

# Sort imports (if isort is installed)
isort .

# Type checking (if mypy is installed)
mypy src/
```

### Start Script Environment Variables

The `scripts/start.sh` script supports configuration via environment variables:

- `HOST`/`GRADIO_HOST` (default: 127.0.0.1)
- `PORT`/`GRADIO_PORT` (default: 7861)
- `OPEN_BROWSER` (default: 0) - set to 1 to open browser automatically
- `FORCE_KILL` (default: 0) - set to 1 to kill existing processes on port
- `BACKGROUND` (default: 0) - set to 1 to run in background

## Architecture

### Core Components

**Main Application (`app.py`)**

- Entry point with Gradio web interface
- Orchestrates all components through `MarkdownVectorApp` class
- Handles file upload, processing, search, and management workflows

**Text Processing (`src/`)**

- `text_splitter.py` - Splits documents into chunks with configurable size and overlap
- `file_processor.py` - Validates and processes uploaded Markdown files
- `embedding_provider.py` - Interfaces with OpenAI's text-embedding-3-small model
- `vector_database.py` - ChromaDB integration for vector storage and retrieval
- `markdown_cleaner.py` - **NEW**: Removes Markdown format symbols to optimize RAG retrieval

### Data Flow

1. User uploads Markdown files via Gradio interface
2. Files validated by `FileProcessor` (extension, size limits)
3. **NEW**: Content preprocessed by `MarkdownCleaner` to remove format symbols
4. Content split into chunks by `TextSplitter`
5. Chunks embedded using OpenAI API via `EmbeddingProvider`
6. Vectors stored in ChromaDB via `VectorDatabase`
7. Search queries embedded and matched against stored vectors

### Database Schema

ChromaDB collection stores:

- Document chunks as text
- OpenAI embeddings as vectors
- Metadata: `source_filename`, `chunk_index`, `start`, `end` positions

### Configuration

- Default chunk size: 1000 characters
- Default chunk overlap: 200 characters
- Default embedding model: text-embedding-3-small
- Default max file size: 5MB
- Database directory: `./chroma_db` or configurable via `CHROMA_DB_DIRECTORY`

### Environment Variables

Required:

- `OPENAI_API_KEY` - OpenAI API key for embeddings

Optional:

- `CHROMA_DB_DIRECTORY` - Vector database storage location
- `COLLECTION_NAME` - ChromaDB collection name
- `DEFAULT_CHUNK_SIZE` - Text splitting chunk size
- `DEFAULT_CHUNK_OVERLAP` - Text splitting overlap
- `MODEL_NAME` - OpenAI embedding model
- `MAX_FILE_SIZE_MB` - Maximum file size limit

**Markdown Preprocessing**:

- `MARKDOWN_CLEANING_ENABLED` (default: true) - Enable/disable Markdown format cleaning
- `MARKDOWN_CLEANING_STRATEGY` (default: balanced) - Cleaning strategy (conservative/balanced/aggressive)
- `PRESERVE_CODE_BLOCKS` (default: true) - Keep code block content
- `PRESERVE_HEADINGS_AS_CONTEXT` (default: true) - Convert headings to context text

### Key Design Patterns

- Component separation: each module handles single responsibility
- Dependency injection: components passed to main app class
- Error handling: validation at file processing level
- Configuration flexibility: environment variable overrides
- Fallback database location: uses `./chroma_db` if configured location unavailable

## Markdown Preprocessing Feature

### Overview

The new `MarkdownCleaner` component removes Markdown format symbols before vectorization to improve RAG retrieval accuracy. Format symbols like `**`, `*`, `#`, `[]`, etc. can interfere with semantic similarity calculations.

### Cleaning Strategies

- **Conservative**: Removes only basic formatting (`**bold**`, `*italic*`, `` `code` ``)
- **Balanced**: Removes formatting, links, quotes, lists while preserving content
- **Aggressive**: Maximum cleanup, removes all format symbols

### Configuration Options

- Enable/disable cleaning per upload
- Choose cleaning strategy via UI or environment variables
- Preserve code blocks and headings independently
- Preview cleaning effects before processing

### Performance Impact

Evaluation shows 21-30% reduction in text length with 100% keyword preservation and 50-70% reduction in format symbol density.

### Usage Examples

```bash
# Environment configuration
MARKDOWN_CLEANING_ENABLED=true
MARKDOWN_CLEANING_STRATEGY=balanced
PRESERVE_CODE_BLOCKS=true
```

### Test Cases

- Unit tests: `tests/test_markdown_cleaner.py`
- Integration tests: `tests/test_integration_markdown_cleaning.py`
- Quality evaluation: Run `python evaluate_quality.py`
