"""VTK-Prompt - A CLI tool for generating VTK visualizations using Large Language Models.

This package provides tools to generate VTK Python code and XML files using
LLMs (Anthropic Claude, OpenAI GPT, or NVIDIA NIM models). It also includes
Retrieval-Augmented Generation (RAG) capabilities to improve code generation
by providing relevant examples from the VTK examples corpus.

Main components:
- vtk-prompt: Generate and run VTK Python code
- gen-vtk-file: Generate VTK XML files
- vtk-build-rag: Build a RAG database from VTK examples
- vtk-test-rag: Test the RAG database with queries
"""

from .prompt import parse_args
from .build_rag_db import main as build_rag_db
from .test_rag import main as test_rag
from .generate_files import parse_args as generate_files

__version__ = "0.1.0"
__author__ = "Vicente Adolfo Bolea Sanchez"
__email__ = "vicente.bolea@kitware.com"
__all__ = ["parse_args", "build_rag_db", "test_rag", "generate_files"]

if __name__ == "__main__":
    parse_args()
