# Markdown File Vectorization Service

This is an MVP implementation for converting Markdown files into vectors and storing them in a local Chroma vector database, supporting semantic search and basic management features.

## Features

- Supports uploading single or multiple Markdown files
- Basic format and size validation
- Character-based document splitting
- Uses OpenAI's `text-embedding-3-small` model for vectorization
- Stores vectors in a local Chroma database
- Provides semantic search functionality
- Offers basic file management (list, delete)

## Installation & Setup

### Prerequisites

- Python 3.10+
- OpenAI API key

### Installation Steps

1. Clone or download this repository

2. Install dependencies

```bash
pip install -e .
```

For development environment, install development dependencies:

```bash
pip install -e ".[dev]"
```

3. Set environment variables

Create a `.env` file and add the following:

```plaintext
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Start the application

 You can either run the Python module directly or use the included start script.

 ```bash
 # run with Python directly
 python app.py

 # or use the helper script (recommended)
 ./scripts/start.sh
 ```

2. Open your browser and go to `http://localhost:7861` to use the Gradio interface

### start script options

The repository includes a helper script at `scripts/start.sh` which loads `.env` (if present) and starts the app. It supports the following environment variables and behaviors:

- `HOST` / `GRADIO_HOST` (default `127.0.0.1`) — host to bind Gradio server to
- `PORT` / `GRADIO_PORT` (default `7861`) — port to bind Gradio server to
- `OPEN_BROWSER` (default `1`) — if set to `0` the script will not attempt to open the browser once the server is ready
- `FORCE_KILL` (default `0`) — if set to `1` and the port is already in use, the script will attempt to terminate the process(es) listening on that port and then start the server

Examples:

```bash
# start normally
./scripts/start.sh

# start on a different port and do not open browser
HOST=127.0.0.1 PORT=7777 OPEN_BROWSER=0 ./scripts/start.sh

# force kill any process using the port, then start
FORCE_KILL=1 ./scripts/start.sh
```

Security note: Do not commit real API keys to the repository. Use `.env` locally and keep it in `.gitignore`.

### Upload Files

- Select one or more Markdown files in the "Upload Files" tab
- Adjust splitting parameters if needed
- Click the "Upload and Process" button

### Search Files

- Enter query text in the "Search Files" tab
- Adjust the number of returned results if needed
- Click the "Search" button to view results

### Manage Files

- View saved files in the "File Management" tab
- Select files to delete

## Default Settings

| Parameter   | Default Value            |
|-------------|-------------------------|
| chunk_size  | 1000                    |
| overlap     | 200                     |
| model       | text-embedding-3-small  |
| top_k       | 5                       |

## Project Structure

```text
.
├── app.py                  # Main application and Gradio UI
├── pyproject.toml          # Dependencies and project settings
├── src/
│   ├── __init__.py
│   ├── text_splitter.py    # Document splitter
│   ├── embedding_provider.py  # Embedding model provider
│   ├── vector_database.py  # Vector database management
│   └── file_processor.py   # File processing
├── tests.py                # Unit tests
└── .env                    # Environment variables (create manually)
```

## Running Tests

```bash
pytest
```

## Notes

- This is an MVP implementation and does not include full error handling or optimization
- Vectors are stored on local disk by default; for long-term use, consider setting up a backup mechanism
