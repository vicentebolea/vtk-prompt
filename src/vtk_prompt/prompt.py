#!/bin/bash

from anthropic import Anthropic
import argparse
import os

PYTHON_VERSION = ">=3.10"
VTK_VERSION = "9.3"

CONTEXT = f"""
Write Python source code that uses VTK.

<instructions>
- Only use VTK {VTK_VERSION}.
- Only use python {PYTHON_VERSION} or above python.
</instructions>

<output>
- Only output verbatin python code.
- Only python code
- No explanations
- No ```python marker.
<\output>

<example>
input: Only create a vtkShpere
output: sphere = vtk.vtkSphereSource()
</example>

Request:
[DESCRIPTION]
"""

ROLE_PROMOTION = f"You are a python {PYTHON_VERSION} source code producing entity"


def anthropic_query(message, model, token, max_tokens):
    """Run the query using the Anthropic API"""
    context = CONTEXT.replace("[DESCRIPTION]", message)
    client = Anthropic(api_key=token)
    response = client.messages.create(
        model=model,
        system=ROLE_PROMOTION,
        max_tokens=1000,
        messages=[{"role": "user", "content": context}],
    )

    return response.content[0].text


def run_code(code_string):
    """Execute VTK code using exec()"""
    try:
        exec(code_string, globals(), {})
    except Exception as e:
        print(f"Error executing code: {e}")
        print(code_string)
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
    args = parser.parse_args()

    code = anthropic_query(args.input_string, args.model, args.token, args.max_tokens)
    run_code(code)
