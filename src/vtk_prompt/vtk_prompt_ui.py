#!/usr/bin/env python3

import os
import sys
import asyncio
from pathlib import Path

# Add VTK and Trame imports
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa
from trame.app import get_server
from trame.widgets import vuetify
from trame_vtk.widgets import vtk as vtk_widgets
from trame.ui.vuetify import SinglePageWithDrawerLayout

import vtk

# Import our prompt functionality
from .prompt import (
    anthropic_query,
    anthropic_query_with_rag_snippets,
    get_rag_snippets,
    check_rag_components_available,
    run_code,
)

POST_PROMPT = """<Higher Priority instructions>
    - Do not create a new vtkRenderer
    - Use the injected vtkrenderer object named renderer.
    - Do not manager rendering things.
    - You must connect the actors to the renderer injected object.
    </Higher Priority instructions>"""


class VTKPromptApp:
    def __init__(self):
        self.server = get_server(client_type="vue2")
        self.state = self.server.state
        self.ctrl = self.server.controller

        # Initialize VTK components for trame
        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        self.render_window.OffScreenRenderingOn()  # Prevent external window
        self.render_window.SetSize(800, 600)

        # App state variables
        self.state.query_text = ""
        self.state.generated_code = ""
        self.state.is_loading = False
        self.state.use_rag = False
        self.state.error_message = ""

        # API configuration state
        self.state.model = "claude-3-5-haiku-latest"
        self.state.max_tokens = 1000
        self.state.available_models = [
            "claude-3-5-haiku-latest",
            "claude-sonnet-4-20250514",
        ]

        # Build UI
        self._build_ui()

        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            self.state.error_message = "ANTHROPIC_API_KEY environment variable not set"
            return

    def generate_code(self):
        """Generate VTK code from user query."""
        self._generate_and_execute_code()

    def clear_scene(self):
        """Clear the VTK scene."""
        self.renderer.RemoveAllViewProps()
        self.ctrl.view_update()

    def reset_camera(self):
        """Reset camera view."""
        self.renderer.ResetCamera()
        self.ctrl.view_update()

    def _generate_and_execute_code(self):
        """Generate VTK code using Anthropic API and execute it."""
        if not self.state.query_text.strip():
            self.state.error_message = "Please enter a query"
            return

        self.state.is_loading = True
        self.state.error_message = ""

        try:
            # Generate code using prompt functionality - reuse existing methods
            if self.state.use_rag and check_rag_components_available():
                # Use RAG-enhanced generation
                rag_snippets = get_rag_snippets(self.state.query_text, top_k=5)
                if rag_snippets:
                    context_snippets = "\n\n".join(rag_snippets["code_snippets"])
                    generated_code = anthropic_query_with_rag_snippets(
                        POST_PROMPT + self.state.query_text,
                        self.state.model,
                        self.api_key,
                        int(self.state.max_tokens),
                        context_snippets,
                        verbose=False,
                    )
                else:
                    # Fall back to regular generation
                    generated_code = anthropic_query(
                        POST_PROMPT + self.state.query_text,
                        self.state.model,
                        self.api_key,
                        int(self.state.max_tokens),
                        verbose=False,
                    )
            else:
                # Regular generation without RAG
                generated_code = anthropic_query(
                    POST_PROMPT + self.state.query_text,
                    self.state.model,
                    self.api_key,
                    int(self.state.max_tokens),
                    verbose=False,
                )

            self.state.generated_code = generated_code

            # Execute the generated code using the existing run_code method
            # But we need to modify it to work with our renderer
            self._execute_with_renderer(generated_code)

        except Exception as e:
            self.state.error_message = f"Error generating code: {str(e)}"
        finally:
            self.state.is_loading = False

    def _execute_with_renderer(self, code_string):
        """Execute VTK code with our renderer using prompt.py's run_code logic."""
        try:
            # Clear previous actors
            self.renderer.RemoveAllViewProps()

            # Use the same code cleaning logic from prompt.py
            pos = code_string.find("import vtk")
            if pos != -1:
                code_string = code_string[pos:]

            # Ensure vtk is imported
            code_segment = code_string
            if "import vtk" not in code_segment:
                code_segment = "import vtk\n" + code_segment

            # Create execution globals with our renderer available
            exec_globals = {
                "vtk": vtk,
                "renderer": self.renderer,
            }

            self.renderWindowInteractor = vtk.vtkRenderWindowInteractor()
            self.renderWindowInteractor.SetRenderWindow(self.render_window)
            self.renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

            exec(code_segment, exec_globals, {})

            # Reset camera and update view
            self.renderer.ResetCamera()
            self.renderer.Render()
            self.ctrl.view_update()

        except Exception as e:
            self.state.error_message = f"Error executing code: {str(e)}"

    def _build_ui(self):
        """Build a simplified Vuetify UI."""
        # Initialize drawer state as collapsed
        self.state.main_drawer = False

        with SinglePageWithDrawerLayout(self.server) as layout:
            layout.title.set_text("VTK Prompt Generator")
            with layout.toolbar:
                vuetify.VSpacer()
                vuetify.VSwitch(
                    v_model=("$vuetify.theme.dark"),
                    hide_details=True,
                    dense=True,
                    label="Dark Mode",
                )

            with layout.drawer as drawer:
                drawer.width = 300

                with vuetify.VListItem():
                    with vuetify.VListItemContent():
                        vuetify.VListItemTitle(
                            "Settings", style="font-size: 18px; font-weight: bold;"
                        )
                vuetify.VDivider()

            with layout.content:
                with vuetify.VContainer(fluid=True):
                    with vuetify.VRow():
                        # Left panel - Input and controls
                        with vuetify.VCol(cols=4):
                            with vuetify.VCard():
                                with vuetify.VCardTitle():
                                    "VTK Code Generator"

                                with vuetify.VCardText():
                                    # Model selection
                                    vuetify.VSelect(
                                        label="Model",
                                        v_model=("model", "claude-3-5-haiku-latest"),
                                        items=("available_models", []),
                                        dense=True,
                                    )

                                    # Max tokens input
                                    vuetify.VTextField(
                                        label="Max Tokens",
                                        v_model=("max_tokens", 1000),
                                        type="number",
                                        dense=True,
                                        style="margin-bottom: 16px;",
                                    )

                                    # Query input
                                    vuetify.VTextarea(
                                        label="Describe VTK visualization",
                                        v_model=("query_text", ""),
                                        rows=3,
                                        placeholder="e.g., Create a red sphere",
                                    )

                                    # RAG option
                                    vuetify.VCheckbox(
                                        v_model=("use_rag", False),
                                        label="Use RAG",
                                    )

                                    # Generate button
                                    vuetify.VBtn(
                                        "Generate Code",
                                        color="primary",
                                        block=True,
                                        loading=("is_loading", False),
                                        click=self.generate_code,
                                    )

                                    # Clear button
                                    vuetify.VBtn(
                                        "Clear Scene",
                                        click=self.clear_scene,
                                        style="margin-top: 10px;",
                                    )

                                    # Error message
                                    vuetify.VAlert(
                                        "{{ error_message }}",
                                        type="error",
                                        v_show=("error_message", ""),
                                    )

                                    # Generated code
                                    vuetify.VTextarea(
                                        label="Generated Code",
                                        v_model=("generated_code", ""),
                                        readonly=True,
                                        rows=10,
                                        style="font-family: monospace;",
                                    )

                        # Right panel - VTK viewer
                        with vuetify.VCol(cols=8):
                            with vuetify.VCard():
                                with vuetify.VCardTitle():
                                    "VTK Visualization"

                                with vuetify.VCardText():
                                    # VTK render window
                                    view = vtk_widgets.VtkRemoteView(
                                        self.render_window,
                                        ref="view",
                                        style="width: 100%; height: 400px;",
                                    )
                                    self.ctrl.view_update = view.update
                                    self.ctrl.view_reset_camera = view.reset_camera

    def start(self):
        """Start the trame server."""
        self.server.start()


def main():
    """Main entry point for the trame app."""

    # Check if API key is set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it to use the code generation features")

    # Create and start the app
    app = VTKPromptApp()
    app.start()


if __name__ == "__main__":
    main()
