#!/bin/bash

from anthropic import Anthropic
import argparse
import os
import json

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
<\output>

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

tools = [
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


def load_class_snippets(vtkclass):
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
    with open("data/examples/index.json") as f:
        vtk_classes = " ".join(list(json.load(f).keys()))

    context = CONTEXT.replace("[DESCRIPTION]", message)
    tools_ops = []
    if enable_rag:
        context = context.replace("[LIST_VTK_CLASSES]", vtk_classes)
        tools_ops = tools
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
            tools=tools,
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
            tools=tools,
        )
    if response.stop_reason == "tool_use":
        print("Anthropic asking tool again, not implemented yet")
        sys.exit(1)

    return response.content[0].text


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
    parser.add_argument(
        "-m", "--model", default="claude-3-5-haiku-latest", help="Model to run AI"
    )
    parser.add_argument(
        "-t",
        "--token",
        default=os.environ.get("ANTHROPIC_API_KEY"),
        help="Token for Anthropic",
    )
    parser.add_argument(
        "-k", "--max-tokens", type=int, default=1000, help="Max # of tokens"
    )

    parser.add_argument(
        "-r", "--rag", action="store_true", default=False, help="Use experimental RAG"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help="Show source code"
    )
    args = parser.parse_args()

    code = anthropic_query(
        args.input_string,
        args.model,
        args.token,
        args.max_tokens,
        args.rag,
        args.verbose,
    )
    run_code(code, args.verbose)
