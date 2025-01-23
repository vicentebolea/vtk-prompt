#!/bin/bash

from anthropic import Anthropic
import argparse
import os
import json

PYTHON_VERSION = ">=3.10"
VTK_VERSION = "9.3"

CONTEXT = f"""
Write only text that is the content of a XML VTK file.

<instructions>
- NO COMMENTS, ONLY CONTENT OF THE FILE
- Only use VTK {VTK_VERSION} basic components.
</instructions>

<output>
- Only output verbatin python code.
- No explanations
- No ```python marker.
<\output>

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


ROLE_PROMOTION = f"You are a XML VTK file generator, the generated file will be read by VTK file reader"


def anthropic_query(message, model, token, max_tokens):
    """Run the query using the Anthropic API"""
    vtk_classes = str()
    with open("data/examples/index.json") as f:
        vtk_classes = " ".join(list(json.load(f).keys()))

    context = CONTEXT.replace("[DESCRIPTION]", message)
    tools_ops = []
    client = Anthropic(api_key=token)

    response = client.messages.create(
        model=model,
        system=ROLE_PROMOTION,
        max_tokens=4096,
        messages=[{"role": "user", "content": context}],
    )

    return response.content[0].text


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
    print(code)
