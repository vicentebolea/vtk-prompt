#!/bin/bash

from anthropic import Anthropic
import argparse
import os
import json
import sys
import openai
import importlib.util

PYTHON_VERSION = ">=3.10"
VTK_VERSION = "9.3"

CONTEXT = f"""
Write only python source code that uses VTK.

<instructions>
- DO NOT READ OUTSIDE DATA
- DO NOT DEFINE FUNCTIONS
- NO TEXT, ONLY SOURCE CODE
- ONLY import VTK and numpy if needed
- Only use VTK {VTK_VERSION} basic components.
- Only use python {PYTHON_VERSION} or above python.
- If declared, use the vtkclass tool once if needed
</instructions>

<output>
- Only output verbatin python code.
- Only VTK library
- No explanations
- No ```python marker.
</output>

<vtkclasses_available>
[LIST_VTK_CLASSES]
</vtkclasses_available>

<example>
input: Only create a vtkShpere
output: sphere = vtk.vtkSphereSource()
</example>

Request:
[DESCRIPTION]

"""
ROLE_PROMOTION = f"You are a python {PYTHON_VERSION} source code producing entity, your output will be fed to a python interpreter"

anthropic_tools = [
    {
        "name": "get_example",
        "description": "Get the a VTK Python example given a vtk class",
        "input_schema": {
            "type": "object",
            "properties": {
                "classes_name": {
                    "type": "string",
                    "description": "The name of the comma separated vtk classes that we want to lookup an example for",
                }
            },
            "required": ["classes_name"],
        },
    }
]

openai_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_example",
            "description": "Get the a VTK Python example given a vtk class",
            "parameters": {
                "type": "object",
                "properties": {
                    "classes_name": {
                        "type": "string",
                        "description": "The name of the comma separated vtk classes that we want to lookup an example for",
                    }
                },
                "required": ["classes_name"],
            },
        },
    }
]


def check_rag_components_available():
    """Check if rag-components are available"""
    return (importlib.util.find_spec("chromadb") is not None and 
            os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "rag-components")))


def setup_rag_path():
    """Add rag-components to the Python path"""
    rag_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "rag-components")
    if rag_path not in sys.path:
        sys.path.append(rag_path)


def get_rag_snippets(query, collection_name="vtk-examples", database_path="./db/codesage-codesage-large-v2", top_k=5):
    """Get code snippets from the RAG database"""
    setup_rag_path()
    try:
        import query_db
        client = query_db.initialize_db(database_path)
        results = query_db.query_db(query, collection_name, top_k, client)
        return {
            "code_snippets": results["code_documents"],
            "text_snippets": results["text_documents"],
            "code_metadata": results["code_metadata"]
        }
    except Exception as e:
        print(f"Error using RAG components: {e}")
        return None


def load_class_snippets(vtkclass):
    """Load code snippets for a given VTK class"""
    output = f"<{vtkclass}>"
    # check if a file exists for the vtk class
    if os.path.isfile(f"data/examples/pp/{vtkclass}"):
        with open(f"data/examples/pp/{vtkclass}") as f:
            output += f.read()
    else:
        output += "cannot be used"

    return output + f"</{vtkclass}>"


def anthropic_query(message, model, token, max_tokens, enable_rag, verbose):
    """Run the query using the Anthropic API"""
    vtk_classes = str()
    context = CONTEXT.replace("[DESCRIPTION]", message)
    tools_ops = []
    
    if enable_rag:
        # Try to use RAG components first
        if check_rag_components_available():
            rag_snippets = get_rag_snippets(message)
            if rag_snippets:
                # Use RAG snippets for context
                context_snippets = "\n\n".join(rag_snippets["code_snippets"])
                return anthropic_query_with_rag_snippets(message, model, token, max_tokens, context_snippets, verbose)
        
        # Fallback to old method if RAG components not available or failed
        with open("data/examples/index.json") as f:
            vtk_classes = " ".join(list(json.load(f).keys()))
        context = context.replace("[LIST_VTK_CLASSES]", vtk_classes)
        tools_ops = anthropic_tools

    client = Anthropic(api_key=token)

    num_tokens = client.messages.count_tokens(
        model=model,
        system=ROLE_PROMOTION,
        messages=[{"role": "user", "content": context}],
        tools=tools_ops,
    )
    if verbose:
        print(f"Number of tokens: {num_tokens}")

    response = client.messages.create(
        model=model,
        system=ROLE_PROMOTION,
        max_tokens=num_tokens.input_tokens,
        messages=[{"role": "user", "content": context}],
        tools=tools_ops,
    )

    if response.stop_reason == "tool_use":
        output = str()
        for block in response.content:
            if block.type == "tool_use":
                if "classes_name" in block.input:
                    classes = block.input["classes_name"]
                    tool_use_id = block.id
                    for class_ in classes.split(","):
                        output = load_class_snippets(class_)

        num_tokens = client.messages.count_tokens(
            model=model,
            system=ROLE_PROMOTION,
            messages=[
                {"role": "user", "content": context},
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": output,
                        }
                    ],
                },
                {"role": "assistant", "content": "import vtk"},
            ],
            tools=anthropic_tools,
        )
        if verbose:
            print(f"Number of tokens: {num_tokens}")

        response = client.messages.create(
            model=model,
            system=ROLE_PROMOTION,
            max_tokens=8192,
            messages=[
                {"role": "user", "content": context},
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": output,
                        }
                    ],
                },
                {"role": "assistant", "content": "import vtk"},
            ],
            tools=anthropic_tools,
        )
    if response.stop_reason == "tool_use":
        print("Anthropic asking tool again, not implemented yet")
        sys.exit(1)

    return response.content[0].text


def anthropic_query_with_rag_snippets(message, model, token, max_tokens, context_snippets, verbose):
    """Run the query using the Anthropic API with RAG snippets as context"""
    # Enhanced context with RAG snippets
    enhanced_context = f"""
Write only python source code that uses VTK.

<instructions>
- DO NOT READ OUTSIDE DATA
- DO NOT DEFINE FUNCTIONS
- NO TEXT, ONLY SOURCE CODE
- ONLY import VTK and numpy if needed
- Only use VTK {VTK_VERSION} basic components.
- Only use python {PYTHON_VERSION} or above python.
- Use the example code snippets below for reference
</instructions>

<vtk_examples>
{context_snippets}
</vtk_examples>

<output>
- Only output verbatin python code.
- Only VTK library
- No explanations
- No ```python marker.
</output>

Request:
{message}
"""

    client = Anthropic(api_key=token)
    
    response = client.messages.create(
        model=model,
        system=ROLE_PROMOTION,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": enhanced_context}],
    )

    return response.content[0].text


def openai_query(message, model, api_key, max_tokens, enable_rag, verbose, base_url=None):
    """Run the query using the OpenAI compatible API (works with NVIDIA NIM)"""
    context = CONTEXT.replace("[DESCRIPTION]", message)
    tools_ops = []
    
    if enable_rag:
        # Try to use RAG components first
        if check_rag_components_available():
            rag_snippets = get_rag_snippets(message)
            if rag_snippets:
                # Use RAG snippets for context
                context_snippets = "\n\n".join(rag_snippets["code_snippets"])
                return openai_query_with_rag_snippets(message, model, api_key, max_tokens, context_snippets, verbose, base_url)
        
        # Fallback to old method if RAG components not available or failed
        with open("data/examples/index.json") as f:
            vtk_classes = " ".join(list(json.load(f).keys()))
        context = context.replace("[LIST_VTK_CLASSES]", vtk_classes)
        tools_ops = openai_tools

    client = openai.OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ROLE_PROMOTION},
            {"role": "user", "content": context}
        ],
        max_tokens=max_tokens,
        tools=tools_ops if enable_rag else None,
    )

    if hasattr(response, "choices") and len(response.choices) > 0:
        message = response.choices[0].message

        # Check if tool was called
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "get_example":
                    try:
                        args = json.loads(tool_call.function.arguments)
                        if "classes_name" in args:
                            classes = args["classes_name"]
                            output = ""
                            for class_ in classes.split(","):
                                output = load_class_snippets(class_)

                            # Second call with the tool results
                            response = client.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": ROLE_PROMOTION},
                                    {"role": "user", "content": context},
                                    {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                                    {"role": "tool", "tool_call_id": tool_call.id, "content": output},
                                ],
                                max_tokens=max_tokens,
                            )
                    except Exception as e:
                        print(f"Error processing tool call: {e}")

        return response.choices[0].message.content

    return "No response generated"


def openai_query_with_rag_snippets(message, model, api_key, max_tokens, context_snippets, verbose, base_url=None):
    """Run the query using the OpenAI API with RAG snippets as context"""
    # Enhanced context with RAG snippets
    enhanced_context = f"""
Write only python source code that uses VTK.

<instructions>
- DO NOT READ OUTSIDE DATA
- DO NOT DEFINE FUNCTIONS
- NO TEXT, ONLY SOURCE CODE
- ONLY import VTK and numpy if needed
- Only use VTK {VTK_VERSION} basic components.
- Only use python {PYTHON_VERSION} or above python.
- Use the example code snippets below for reference
</instructions>

<vtk_examples>
{context_snippets}
</vtk_examples>

<output>
- Only output verbatin python code.
- Only VTK library
- No explanations
- No ```python marker.
</output>

Request:
{message}
"""

    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ROLE_PROMOTION},
            {"role": "user", "content": enhanced_context}
        ],
        max_tokens=max_tokens,
    )

    if hasattr(response, "choices") and len(response.choices) > 0:
        return response.choices[0].message.content
    
    return "No response generated"


def run_code(code_string, verbose):
    """Execute VTK code using exec()"""
    # Remove notes before the import
    pos = code_string.find("import vtk")
    if pos != -1:
        code_string = code_string[pos:]

    code_segment = "import vtk\n" + code_string
    if verbose:
        print(code_segment)
    try:
        exec(code_segment, globals(), {})
    except Exception as e:
        print(f"Error executing code: {e}")
        if not verbose:
            print(code_segment)
        return None


def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser(prog="vtk-prompt", description="VTK LLM prompt")
    parser.add_argument("input_string")

    # Provider selection
    provider_group = parser.add_argument_group("LLM Provider")
    provider_group.add_argument(
        "--provider",
        choices=["anthropic", "openai", "nim"],
        default="anthropic",
        help="LLM provider to use (anthropic, openai, or nim)"
    )

    # Model parameters
    parser.add_argument(
        "-m", "--model", default="claude-3-5-haiku-latest", help="Model name to use"
    )
    parser.add_argument(
        "-k", "--max-tokens", type=int, default=1000, help="Max # of tokens"
    )

    # API configuration
    parser.add_argument(
        "-t", "--token", help="API token (defaults to environment variable based on provider)"
    )
    parser.add_argument(
        "--base-url", help="Base URL for API (useful for NIM or proxies)"
    )

    # Feature flags
    parser.add_argument(
        "-r", "--rag", action="store_true", default=False, help="Use experimental RAG"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help="Show source code"
    )
    
    # RAG specific options
    rag_group = parser.add_argument_group("RAG Options")
    rag_group.add_argument(
        "--collection", default="vtk-examples", help="Collection name for RAG"
    )
    rag_group.add_argument(
        "--database", default="./db/codesage-codesage-large-v2", help="Database path for RAG"
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

    # Set default models if not specified
    if args.model == "claude-3-5-haiku-20240307" and args.provider != "anthropic":
        if args.provider == "openai":
            args.model = "gpt-4o"
        elif args.provider == "nim":
            args.model = "meta/llama3-70b-instruct"

    # Execute the query based on provider
    if args.provider == "anthropic":
        if args.rag and check_rag_components_available():
            rag_snippets = get_rag_snippets(
                args.input_string, 
                collection_name=args.collection,
                database_path=args.database,
                top_k=args.top_k
            )
            if rag_snippets:
                context_snippets = "\n\n".join(rag_snippets["code_snippets"])
                code = anthropic_query_with_rag_snippets(
                    args.input_string,
                    args.model,
                    args.token,
                    args.max_tokens,
                    context_snippets,
                    args.verbose
                )
            else:
                code = anthropic_query(
                    args.input_string,
                    args.model,
                    args.token,
                    args.max_tokens,
                    args.rag,
                    args.verbose,
                )
        else:
            code = anthropic_query(
                args.input_string,
                args.model,
                args.token,
                args.max_tokens,
                args.rag,
                args.verbose,
            )
    else:  # openai or nim
        if args.rag and check_rag_components_available():
            rag_snippets = get_rag_snippets(
                args.input_string, 
                collection_name=args.collection,
                database_path=args.database,
                top_k=args.top_k
            )
            if rag_snippets:
                context_snippets = "\n\n".join(rag_snippets["code_snippets"])
                code = openai_query_with_rag_snippets(
                    args.input_string,
                    args.model,
                    args.token,
                    args.max_tokens,
                    context_snippets,
                    args.verbose,
                    args.base_url
                )
            else:
                code = openai_query(
                    args.input_string,
                    args.model,
                    args.token,
                    args.max_tokens,
                    args.rag,
                    args.verbose,
                    args.base_url,
                )
        else:
            code = openai_query(
                args.input_string,
                args.model,
                args.token,
                args.max_tokens,
                args.rag,
                args.verbose,
                args.base_url,
            )

    run_code(code, args.verbose)
