#!/usr/bin/env python3

import argparse
import os
import sys
import importlib.util
from pathlib import Path

def setup_rag_path():
    """Add rag-components to the Python path"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    rag_path = os.path.join(project_root, "rag-components")
    if rag_path not in sys.path:
        sys.path.append(rag_path)
    return rag_path

def main():
    parser = argparse.ArgumentParser(description="Build RAG database for VTK examples")
    parser.add_argument(
        "--examples-dir",
        type=str,
        default="data/examples",
        help="Directory containing VTK examples (default: data/examples)"
    )
    parser.add_argument(
        "--database",
        type=str,
        default="./db/codesage-codesage-large-v2",
        help="Database path (default: ./db/codesage-codesage-large-v2)"
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="vtk-examples",
        help="Collection name in the database (default: vtk-examples)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="codesage/codesage-large-v2",
        help="Embedding model name (default: codesage/codesage-large-v2)"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="python",
        help="Language of the examples (default: python)"
    )

    args = parser.parse_args()

    breakpoint()
    # Setup RAG path
    rag_path = setup_rag_path()

    # Import populate_db from rag-components
    try:
        sys.path.insert(0, rag_path)
        from populate_db import fill_database
    except ImportError as e:
        print(f"Failed to import from rag-components: {e}")
        sys.exit(1)

    # Check if examples directory exists
    examples_dir = Path(args.examples_dir)
    if not examples_dir.exists() or not examples_dir.is_dir():
        print(f"Error: Examples directory '{args.examples_dir}' does not exist or is not a directory")
        sys.exit(1)

    # Get all Python files in the examples directory
    files = list(examples_dir.glob("**/*.py"))
    if not files:
        print(f"No Python files found in '{args.examples_dir}'")
        sys.exit(1)

    print(f"Found {len(files)} Python files in '{args.examples_dir}'")

    # Create database directory if it doesn't exist
    database_dir = Path(args.database).parent
    database_dir.mkdir(parents=True, exist_ok=True)

    # Build the RAG database
    print(f"Building RAG database at '{args.database}' using embedding model '{args.model}'...")
    fill_database(
        files=files,
        database_path=args.database,
        embedding_model=args.model,
        language=args.language,
        collection_name=args.collection_name,
    )

    print(f"Successfully built RAG database at '{args.database}'")
    print(f"You can now use the RAG database with vtk-prompt by running:")
    print(f"vtk-prompt \"your query\" -r --database {args.database} --collection {args.collection_name}")

if __name__ == "__main__":
    main()
