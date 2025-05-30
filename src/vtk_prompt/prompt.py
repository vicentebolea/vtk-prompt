#!/usr/bin/env python3

from anthropic import Anthropic
from pathlib import Path
import argparse
import os
import json
import sys
import openai
import importlib.util
import vtk

PYTHON_VERSION = ">=3.10"
VTK_VERSION = vtk.__version__

CONTEXT_BASE = f"""
Write only python source code that uses VTK.

<instructions>
- DO NOT READ OUTSIDE DATA
- DO NOT DEFINE FUNCTIONS
- NO TEXT, ONLY SOURCE CODE
- ONLY import VTK and numpy if needed
- Only use {VTK_VERSION=} python basic components.
- Only use {PYTHON_VERSION=} or above.
</instructions>

<output>
- Only output verbatin python code.
- Only VTK library
- No explanations
- No ```python marker.
</output>

<example>
input: Only create a vtkShpere
output: sphere = vtk.vtkSphereSource()
</example>
"""

CONTEXT_NO_RAG = (
    CONTEXT_BASE
    + """

Request:
{request}
"""
)

CONTEXT_RAG = (
    CONTEXT_BASE
    + """

<extra_instructions>
- Refer to the below vtk_examples snippets, this is the the main source of thruth
</extra_instructions>

<vtk_examples>
{context_snippets}
</vtk_examples>

Request:
{request}
"""
)

ROLE_PROMOTION = f"You are a python {PYTHON_VERSION} source code producing entity, your output will be fed to a python interpreter"


def check_rag_components_available():
    """Check if RAG components are available and installed."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    rag_components_path = repo_root / "rag-components"

    return (
        importlib.util.find_spec("chromadb") is not None
        and rag_components_path.exists()
    )


def setup_rag_path():
    """Add rag-components directory to the Python path.

    Returns:
        The path to the rag-components directory
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    rag_path = str(repo_root / "rag-components")

    if rag_path not in sys.path:
        sys.path.append(rag_path)

    return rag_path


def get_rag_snippets(
    query,
    collection_name="vtk-examples",
    database_path="./db/codesage-codesage-large-v2",
    top_k=5,
):
    """Get code snippets from the RAG database.

    Args:
        query: The query to search for in the database
        collection_name: The name of the collection in the database
        database_path: The path to the database
        top_k: The number of top results to return

    Returns:
        A dictionary containing code snippets, text snippets, and metadata
    """
    setup_rag_path()
    try:
        import query_db

        # Initialize the database client
        client = query_db.initialize_db(database_path)

        # Query the database for relevant snippets
        results = query_db.query_db(query, collection_name, top_k, client)

        # Extract relevant URLs for attribution
        relevant_examples = []
        for item in results["code_metadata"]:
            if "original_id" in item:
                relevant_examples.append(item["original_id"])

        # Add any code examples from text metadata
        for item in results["text_metadata"]:
            if "code" in item:
                relevant_examples.append(item["code"])

        # Remove duplicates
        relevant_examples = list(set(relevant_examples))

        return {
            "code_snippets": results["code_documents"],
            "text_snippets": results["text_documents"],
            "code_metadata": results["code_metadata"],
            "references": relevant_examples,
        }
    except Exception as e:
        print(f"Error using RAG components: {e}")
        return None


def load_class_snippets(vtkclass):
    """Load code snippets for a given VTK class.

    Args:
        vtkclass: The name of the VTK class to load snippets for

    Returns:
        The snippets wrapped in XML tags
    """
    output = f"<{vtkclass}>"
    examples_path = Path("data/examples/pp") / vtkclass

    if examples_path.is_file():
        output += examples_path.read_text()
    else:
        output += "cannot be used"

    return output + f"</{vtkclass}>"


def anthropic_query(message, model, token, max_tokens, verbose):
    """Run the query using the Anthropic API.

    Args:
        message: The user's query
        model: The model to use
        token: The API token
        max_tokens: Maximum tokens to generate
        verbose: Whether to print verbose output

    Returns:
        The generated code from the API
    """
    context = CONTEXT_NO_RAG.format(request=message)
    if verbose:
        print("CONTEXT: " + context)

    client = Anthropic(api_key=token)

    # Make the API call without tools
    response = client.messages.create(
        model=model,
        system=ROLE_PROMOTION,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": context}],
    )

    # Return the final text response
    return response.content[0].text


def anthropic_query_with_rag_snippets(
    message, model, token, max_tokens, context_snippets, verbose, references=None
):
    """Run the query using the Anthropic API with RAG snippets as context.

    Args:
        message: The user's query
        model: The model to use
        token: The API token
        max_tokens: Maximum tokens to generate
        context_snippets: Code snippets from RAG to include as context
        verbose: Whether to print verbose output
        references: Optional list of reference sources for the snippets

    Returns:
        The generated code from the API
    """
    # Create enhanced context with RAG snippets

    context = CONTEXT_RAG.format(request=message, context_snippets=context_snippets)

    if verbose:
        print("CONTEXT: " + context)

    # If verbose and we have references, print them
    if verbose and references:
        print("Using examples from:")
        for ref in references:
            print(f"- {ref}")

    client = Anthropic(api_key=token)

    # If token count is needed in verbose mode
    if verbose:
        num_tokens = client.messages.count_tokens(
            model=model,
            system=ROLE_PROMOTION,
            messages=[{"role": "user", "content": context}],
        )
        print(
            f"Input tokens: {num_tokens.input_tokens}, Output tokens limit: {max_tokens}"
        )

    response = client.messages.create(
        model=model,
        system=ROLE_PROMOTION,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": context}],
    )

    return response.content[0].text


def openai_query(message, model, api_key, max_tokens, verbose, base_url=None):
    """Run the query using the OpenAI compatible API (works with NVIDIA NIM).

    Args:
        message: The user's query
        model: The model to use
        api_key: The API key
        max_tokens: Maximum tokens to generate
        verbose: Whether to print verbose output
        base_url: Optional custom API endpoint URL

    Returns:
        The generated code from the API
    """
    context = CONTEXT_NO_RAG.format(request=message)
    if verbose:
        print("CONTEXT: " + context)

    # Initialize the client
    client = openai.OpenAI(api_key=api_key, base_url=base_url)

    # Make the API call without tools
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ROLE_PROMOTION},
            {"role": "user", "content": context},
        ],
        max_tokens=max_tokens,
    )

    # Process the response
    if hasattr(response, "choices") and len(response.choices) > 0:
        response_message = response.choices[0].message
        return response_message.content or "No content in response"

    return "No response generated"


def openai_query_with_rag_snippets(
    message,
    model,
    api_key,
    max_tokens,
    context_snippets,
    verbose,
    base_url=None,
    references=None,
):
    """Run the query using the OpenAI API with RAG snippets as context.

    Args:
        message: The user's query
        model: The model to use
        api_key: The API key
        max_tokens: Maximum tokens to generate
        context_snippets: Code snippets from RAG to include as context
        verbose: Whether to print verbose output
        base_url: Optional custom API endpoint URL
        references: Optional list of reference sources for the snippets

    Returns:
        The generated code from the API
    """
    context = CONTEXT_RAG.format(request=message, context_snippets=context_snippets)
    if verbose:
        print("CONTEXT: " + context)

    # If verbose and we have references, print them
    if verbose and references:
        print("Using examples from:")
        for ref in references:
            print(f"- {ref}")

    # Initialize the client
    client = openai.OpenAI(api_key=api_key, base_url=base_url)

    # Make the API call
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ROLE_PROMOTION},
            {"role": "user", "content": context},
        ],
        max_tokens=max_tokens,
    )

    # Process the response
    if hasattr(response, "choices") and len(response.choices) > 0:
        return response.choices[0].message.content or "No content in response"

    return "No response generated"


def run_code(code_string, verbose):
    """Execute VTK code using exec().

    Args:
        code_string: The code to execute
        verbose: Whether to print the code before execution
    """
    # Clean up the code: remove any text before the first import
    pos = code_string.find("import vtk")
    if pos != -1:
        code_string = code_string[pos:]

    # Ensure vtk is imported
    code_segment = code_string
    if "import vtk" not in code_segment:
        code_segment = "import vtk\n" + code_segment

    # Print the code if in verbose mode
    if verbose:
        print(code_segment)

    # Execute the code
    try:
        exec(code_segment, globals(), {})
    except Exception as e:
        print(f"Error executing code: {e}")
        # Print the code if not already printed and there was an error
        if not verbose:
            print(code_segment)

        # Return None to indicate failure
        return None


def parse_args():
    """Parse command line arguments and execute the appropriate query."""
    parser = argparse.ArgumentParser(
        prog="vtk-prompt", description="Generate and execute VTK code using LLMs"
    )
    parser.add_argument(
        "input_string", help="The code description to generate VTK code for"
    )

    # Provider selection
    provider_group = parser.add_argument_group("LLM Provider")
    provider_group.add_argument(
        "--provider",
        choices=["anthropic", "openai", "nim"],
        default="anthropic",
        help="LLM provider to use (anthropic, openai, or nim)",
    )

    # Model parameters
    parser.add_argument(
        "-m", "--model", default="claude-3-5-haiku-latest", help="Model name to use"
    )
    parser.add_argument(
        "-k", "--max-tokens", type=int, default=1000, help="Max # of tokens to generate"
    )

    # API configuration
    parser.add_argument(
        "-t",
        "--token",
        help="API token (defaults to environment variable based on provider)",
    )
    parser.add_argument(
        "--base-url", help="Base URL for API (useful for NIM or proxies)"
    )

    # Feature flags
    parser.add_argument(
        "-r",
        "--rag",
        action="store_true",
        default=False,
        help="Use RAG to improve code generation",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Show generated source code",
    )

    # RAG specific options
    rag_group = parser.add_argument_group("RAG Options")
    rag_group.add_argument(
        "--collection", default="vtk-examples", help="Collection name for RAG"
    )
    rag_group.add_argument(
        "--database",
        default="./db/codesage-codesage-large-v2",
        help="Database path for RAG",
    )
    rag_group.add_argument(
        "--top-k", type=int, default=5, help="Number of examples to retrieve from RAG"
    )

    args = parser.parse_args()

    # Set default API keys based on provider
    if args.token is None:
        if args.provider == "anthropic":
            args.token = os.environ.get("ANTHROPIC_API_KEY")
        elif args.provider in ["openai", "nim"]:
            args.token = os.environ.get("OPENAI_API_KEY")

        if args.token is None:
            print(f"Error: No API token provided for {args.provider}")
            sys.exit(1)

    # Set default base URL for NIM
    if args.provider == "nim" and args.base_url is None:
        args.base_url = "https://integrate.api.nvidia.com/v1"

    # Set default models if not specified based on provider
    if args.model == "claude-3-5-haiku-20240307" and args.provider != "anthropic":
        if args.provider == "openai":
            args.model = "gpt-4o"
        elif args.provider == "nim":
            args.model = "meta/llama3-70b-instruct"

    generated_code = ""
    if args.rag:
        if not check_rag_components_available():
            print("rag_components not found")
            sys.exit(2)

        rag_snippets = get_rag_snippets(
            args.input_string,
            collection_name=args.collection,
            database_path=args.database,
            top_k=args.top_k,
        )

        if rag_snippets:
            context_snippets = "\n\n".join(rag_snippets["code_snippets"])
            if args.provider == "anthropic":
                generated_code = anthropic_query_with_rag_snippets(
                    args.input_string,
                    args.model,
                    args.token,
                    args.max_tokens,
                    context_snippets,
                    args.verbose,
                    rag_snippets.get("references"),
                )
            else:
                generated_code = openai_query_with_rag_snippets(
                    args.input_string,
                    args.model,
                    args.token,
                    args.max_tokens,
                    context_snippets,
                    args.verbose,
                    args.base_url,
                    rag_snippets.get("references"),
                )
        else:
            print("failed to load rag snippets")
            sys.exit(3)

    else:
        if args.provider == "anthropic":
            generated_code = anthropic_query(
                args.input_string,
                args.model,
                args.token,
                args.max_tokens,
                args.verbose,
            )
        else:  # openai or nim
            generated_code = openai_query(
                args.input_string,
                args.model,
                args.token,
                args.max_tokens,
                args.verbose,
                args.base_url,
            )

    # Run the generated code
    run_code(generated_code, args.verbose)
