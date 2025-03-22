"""VTK-Prompt - A CLI for generating VTK code using LLMs"""

from .prompt import parse_args
from .build_rag_db import main as build_rag_db
from .test_rag import main as test_rag

__version__ = "0.1.0"
__all__ = ["parse_args", "build_rag_db", "test_rag"]

if __name__ == "__main__":
    parse_args()
