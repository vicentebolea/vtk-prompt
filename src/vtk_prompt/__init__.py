"""VTK-Prompt - CLI tool for generating VTK visualizations using LLMs.

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

__version__ = "0.1.0"
__author__ = "Vicente Adolfo Bolea Sanchez"
__email__ = "vicente.bolea@kitware.com"
