#!/usr/bin/env python3

from anthropic import Anthropic
from pathlib import Path
import argparse
import os
import json

PYTHON_VERSION = ">=3.10"
VTK_VERSION = "9.3"

# Context template for prompting the AI to generate VTK XML files
CONTEXT = f"""
Write only text that is the content of a XML VTK file.

<instructions>
- NO COMMENTS, ONLY CONTENT OF THE FILE
- Only use VTK {VTK_VERSION} basic components.
</instructions>

<output>
- Only output verbatim XML content.
- No explanations
- No markup or code blocks
</output>

<example>
input: A VTP file example of a 4 points with temperature and pressure data
output:
<?xml version="1.0"?>
<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">
  <PolyData>
    <Piece NumberOfPoints="4" NumberOfVerts="0" NumberOfLines="0" NumberOfStrips="0" NumberOfPolys="0">
      <!-- Points coordinates -->
      <Points>
        <DataArray type="Float32" NumberOfComponents="3" format="ascii">
          0.0 0.0 0.0
          1.0 0.0 0.0
          0.0 1.0 0.0
          1.0 1.0 0.0
        </DataArray>
      </Points>

      <!-- Point Data (attributes) -->
      <PointData>
        <!-- Temperature data for each point -->
        <DataArray type="Float32" Name="Temperature" format="ascii">
          25.5
          26.7
          24.3
          27.1
        </DataArray>
        <!-- Pressure data for each point -->
        <DataArray type="Float32" Name="Pressure" format="ascii">
          101.3
          101.5
          101.2
          101.4
        </DataArray>
      </PointData>

      <!-- Cell Data (empty in this case) -->
      <CellData>
      </CellData>

      <!-- Vertex definitions (empty in this case) -->
      <Verts>
        <DataArray type="Int32" Name="connectivity" format="ascii">
        </DataArray>
        <DataArray type="Int32" Name="offsets" format="ascii">
        </DataArray>
      </Verts>

      <!-- Line definitions (empty in this case) -->
      <Lines>
        <DataArray type="Int32" Name="connectivity" format="ascii">
        </DataArray>
        <DataArray type="Int32" Name="offsets" format="ascii">
        </DataArray>
      </Lines>

      <!-- Polygon definitions (empty in this case) -->
      <Polys>
        <DataArray type="Int32" Name="connectivity" format="ascii">
        </DataArray>
        <DataArray type="Int32" Name="offsets" format="ascii">
        </DataArray>
      </Polys>
    </Piece>
  </PolyData>
</VTKFile>
</example>

Request:
[DESCRIPTION]
"""

# System prompt for the AI
ROLE_PROMOTION = "You are a XML VTK file generator, the generated file will be read by VTK file reader"


def anthropic_query(message, model, token, max_tokens):
    """Run the query using the Anthropic API to generate VTK XML content.

    Args:
        message: The user's description of the VTK file to generate
        model: The model to use
        token: The API token
        max_tokens: Maximum tokens to generate

    Returns:
        The generated XML content
    """
    # Load available VTK classes for context
    examples_path = Path("data/examples/index.json")
    if examples_path.exists():
        vtk_classes = " ".join(json.loads(examples_path.read_text()).keys())
    else:
        vtk_classes = ""

    # Prepare the context with the user's description
    context = CONTEXT.replace("[DESCRIPTION]", message)

    # Initialize the client and make the API call
    client = Anthropic(api_key=token)
    response = client.messages.create(
        model=model,
        system=ROLE_PROMOTION,
        max_tokens=4096,
        messages=[{"role": "user", "content": context}],
    )

    # Return the generated XML content
    return response.content[0].text


def parse_args():
    """Parse command line arguments and generate VTK XML file content."""
    parser = argparse.ArgumentParser(
        prog="gen-vtk-file", description="Generate VTK XML file content using LLMs"
    )

    parser.add_argument("input_string", help="Description of the VTK file to generate")
    parser.add_argument(
        "-m",
        "--model",
        default="claude-3-5-haiku-latest",
        help="Model to use for generation",
    )
    parser.add_argument(
        "-t",
        "--token",
        default=os.environ.get("ANTHROPIC_API_KEY"),
        help="API token for Anthropic (defaults to ANTHROPIC_API_KEY environment variable)",
    )
    parser.add_argument(
        "-k",
        "--max-tokens",
        type=int,
        default=4000,
        help="Maximum number of tokens to generate",
    )
    parser.add_argument(
        "-o", "--output", help="Output file path (if not specified, output to stdout)"
    )

    args = parser.parse_args()

    # Validate token
    if not args.token:
        print(
            "Error: No API token provided. Set ANTHROPIC_API_KEY environment variable or use --token"
        )
        exit(1)

    # Generate the VTK XML content
    xml_content = anthropic_query(
        args.input_string, args.model, args.token, args.max_tokens
    )

    # Output to file or stdout
    if args.output:
        with open(args.output, "w") as f:
            f.write(xml_content)
        print(f"VTK XML content written to {args.output}")
    else:
        print(xml_content)


if __name__ == "__main__":
    parse_args()
