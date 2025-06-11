# VTK Prompt

A command-line interface and web-based UI for generating VTK visualization code using LLMs (Anthropic Claude, OpenAI GPT, and NVIDIA NIM).

![Screenshot from 2025-06-10 22-59-54](https://github.com/user-attachments/assets/4f6223c4-f2d6-49fd-beeb-9797a510f0df)


## Installation

Basic installation:
```bash
pip install -e .
```

With RAG support:
```bash
pip install -e ".[rag]"
```

## Usage

### Web UI (Recommended)

Launch the interactive web interface:

```bash
vtk-prompt-ui
```

The web UI provides:
- **Model Selection**: Choose between Claude models (Haiku, Sonnet 4)
- **Token Control**: Adjust maximum tokens for responses
- **RAG Integration**: Toggle retrieval-augmented generation
- **Live VTK Viewer**: See visualizations rendered in real-time
- **Code Display**: View and copy generated VTK code

Requirements:
- Set `ANTHROPIC_API_KEY` environment variable
- Access the UI at `http://localhost:8080` (default)

### Command Line Interface

```bash
# Basic usage with Anthropic Claude (default)
vtk-prompt "Create a red sphere"

# Using OpenAI GPT models
vtk-prompt "Create a blue cube" --provider openai -t YOUR_OPENAI_TOKEN

# Using NVIDIA NIM with Llama 3
vtk-prompt "Create a cone with 16 resolution" --provider nim -t YOUR_NIM_TOKEN

# Enable RAG (Retrieval Augmented Generation) for better VTK class references
vtk-prompt "Create a cylinder" -r

# Show verbose output including generated code
vtk-prompt "Create a sphere with a custom shader" -v
```

## RAG (Retrieval Augmented Generation)

The RAG feature improves code generation by retrieving relevant VTK code examples from a database. To use RAG:

1. Build the RAG database:
```bash
# Build RAG database using default settings
vtk-build-rag

# Customize the database build
vtk-build-rag --examples-dir data/examples --database ./db/my-database --collection-name vtk-examples
```

2. Test the RAG database (optional):
```bash
# Test the RAG system with a simple query
vtk-test-rag "How to create a cube in VTK"

# Test with custom database settings
vtk-test-rag "vtkSphereSource with custom resolution" --database ./db/my-database --collection my-collection
```

3. Use the RAG database in your queries:
```bash
# Basic RAG usage (uses default database)
vtk-prompt "Create a cone with texture" -r

# Specify a custom database or collection
vtk-prompt "Create a vtkCubeSource" -r --database ./db/my-database --collection my-collection
```

## Environment Variables

You can set the following environment variables to avoid providing tokens on the command line:
- `ANTHROPIC_API_KEY` - For Anthropic Claude models
- `OPENAI_API_KEY` - For OpenAI API or NVIDIA NIM models

## Supported Providers and Models

### Anthropic
- Default model: claude-3-5-haiku-20240307
- Other models: claude-3-opus, claude-3-sonnet, etc.

### OpenAI 
- Default model: gpt-4o
- Other models: gpt-4, gpt-3.5-turbo, etc.

### NVIDIA NIM
- Default model: meta/llama3-70b-instruct
- Other models: mistralai/mixtral-8x7b-instruct, etc.
- Base URL: https://api.nvcf.nvidia.com/v1 (default for NIM provider)

## Advanced Options

```
usage: vtk-prompt [-h] [--provider {anthropic,openai,nim}] [-m MODEL] [-k MAX_TOKENS]
                  [-t TOKEN] [--base-url BASE_URL] [-r] [-v]
                  [--collection COLLECTION] [--database DATABASE] [--top-k TOP_K]
                  input_string

VTK LLM prompt

positional arguments:
  input_string

options:
  -h, --help            show this help message and exit
  -m MODEL, --model MODEL
                        Model name to use
  -k MAX_TOKENS, --max-tokens MAX_TOKENS
                        Max # of tokens
  -t TOKEN, --token TOKEN
                        API token (defaults to environment variable based on provider)
  --base-url BASE_URL   Base URL for API (useful for NIM or proxies)
  -r, --rag             Use experimental RAG
  -v, --verbose         Show source code

LLM Provider:
  --provider {anthropic,openai,nim}
                        LLM provider to use (anthropic, openai, or nim)

RAG Options:
  --collection COLLECTION
                        Collection name for RAG (default: vtk-examples)
  --database DATABASE   Database path for RAG (default: ./db/codesage-codesage-large-v2)
  --top-k TOP_K         Number of examples to retrieve from RAG (default: 5)
```
