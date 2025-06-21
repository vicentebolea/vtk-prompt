#!/usr/bin/env python3

# Add VTK and Trame imports
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa
from trame.app import get_server
from trame.widgets import vuetify, html
from trame_vtk.widgets import vtk as vtk_widgets
from trame.ui.vuetify import SinglePageWithDrawerLayout

import vtk

# Import our prompt functionality
from .prompt import VTKPromptClient

# Import our template system
from .prompts import get_ui_post_prompt

EXPLAIN_RENDERER = (
    "# renderer is a vtkRenderer injected by this webapp"
    + "\n"
    + "# Use your own vtkRenderer in your application"
)


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

        # Initialize render window interactor properly
        self.render_window_interactor = vtk.vtkRenderWindowInteractor()
        self.render_window_interactor.SetRenderWindow(self.render_window)
        self.render_window_interactor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

        # Set a default background and add a simple default scene to prevent segfault
        self.renderer.SetBackground(0.1, 0.1, 0.1)

        # Add a simple coordinate axes as default content
        self._add_default_scene()

        # Initial render
        self.render_window.Render()

    def _add_default_scene(self):
        """Add default coordinate axes to prevent empty scene segfaults."""
        try:
            # Create simple axes
            axes = vtk.vtkAxesActor()
            axes.SetTotalLength(1, 1, 1)
            axes.SetShaftType(0)  # Line shaft
            axes.SetCylinderRadius(0.02)

            # Add to renderer
            self.renderer.AddActor(axes)

            # Reset camera to show axes
            self.renderer.ResetCamera()

        except Exception as e:
            print(f"Warning: Could not add default scene: {e}")

        # App state variables
        self.state.query_text = ""
        self.state.generated_code = ""
        self.state.is_loading = False
        self.state.use_rag = False
        self.state.error_message = ""

        # Token usage tracking
        self.state.input_tokens = 0
        self.state.output_tokens = 0

        # API configuration state
        self.state.use_cloud_models = True  # Toggle between cloud and local
        self.state.tab_index = 0  # Tab navigation state

        # Cloud model configuration
        self.state.provider = "openai"
        self.state.model = "gpt-4o"
        self.state.available_providers = [
            "openai",
            "anthropic",
            "gemini",
            "nim",
        ]
        self.state.available_models = {
            "openai": ["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"],
            "anthropic": [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229",
            ],
            "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
            "nim": [
                "meta/llama3-70b-instruct",
                "meta/llama3-8b-instruct",
                "microsoft/phi-3-medium-4k-instruct",
                "nvidia/llama3-chatqa-1.5-70b",
            ],
        }

        self.state.api_token = "ollama"

        # Build UI
        self._build_ui()

        # Initialize the VTK prompt client
        self._init_prompt_client()

    def _init_prompt_client(self):
        """Initialize the prompt client based on current settings."""
        try:
            # Validate configuration
            validation_error = self._validate_configuration()
            if validation_error:
                self.state.error_message = validation_error
                return

            _ = self._get_base_url()
            api_key = self._get_api_key()

            # For cloud models, API key is usually required
            if self.state.use_cloud_models and not api_key:
                self.state.error_message = (
                    f"API token is required for {self.state.provider}. "
                    "Please enter your API token."
                )
                return

            self.prompt_client = VTKPromptClient(
                collection_name="vtk-examples",
                database_path="./db/codesage-codesage-large-v2",
                verbose=False,
            )
        except ValueError as e:
            self.state.error_message = str(e)

    def _get_api_key(self):
        """Get API key from state (requires manual input in UI)."""
        api_token = getattr(self.state, "api_token", "")
        return api_token.strip() if api_token and api_token.strip() else None

    def _get_base_url(self):
        """Get base URL based on configuration mode."""
        if self.state.use_cloud_models:
            # Use predefined base URLs for cloud providers (OpenAI uses default None)
            base_urls = {
                "anthropic": "https://api.anthropic.com/v1",
                "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
                "nim": "https://integrate.api.nvidia.com/v1",
            }
            return base_urls.get(self.state.provider)
        else:
            # Use local base URL for local models
            local_url = getattr(self.state, "local_base_url", "")
            return local_url.strip() if local_url and local_url.strip() else None

    def _get_model(self):
        """Get model name based on configuration mode."""
        if self.state.use_cloud_models:
            return getattr(self.state, "model", "gpt-4o")
        else:
            local_model = getattr(self.state, "local_model", "")
            return (
                local_model.strip()
                if local_model and local_model.strip()
                else "llama3.2:latest"
            )

    def _get_current_config_summary(self):
        """Get a summary of current configuration for display."""
        if self.state.use_cloud_models:
            return f"☁️ {self.state.provider}/{self.state.model}"
        else:
            base_display = (
                self.state.local_base_url.replace("http://", "").replace("https://", "")
                if self.state.local_base_url
                else "localhost"
            )
            model_display = (
                self.state.local_model if self.state.local_model else "default"
            )
            return f"🏠 {base_display}/{model_display}"

    def _validate_configuration(self):
        """Validate current configuration and return error message if invalid."""
        if self.state.use_cloud_models:
            # Validate cloud configuration
            if not hasattr(self.state, "provider") or not self.state.provider:
                return "Provider is required for cloud models"
            if self.state.provider not in self.state.available_providers:
                return f"Invalid provider: {self.state.provider}"
            if not hasattr(self.state, "model") or not self.state.model:
                return "Model is required for cloud models"
            if self.state.provider in self.state.available_models:
                if (
                    self.state.model
                    not in self.state.available_models[self.state.provider]
                ):
                    return f"Invalid model {self.state.model} for provider {self.state.provider}"
        else:
            # Validate local configuration
            if (
                not hasattr(self.state, "local_base_url")
                or not self.state.local_base_url.strip()
            ):
                return "Base URL is required for local models"
            if (
                not hasattr(self.state, "local_model")
                or not self.state.local_model.strip()
            ):
                return "Model name is required for local models"

            # Basic URL validation
            base_url = self.state.local_base_url.strip()
            if not (base_url.startswith("http://") or base_url.startswith("https://")):
                return "Base URL must start with http:// or https://"

        return None  # No validation errors

    def on_tab_change(self, tab_index):
        """Handle tab change to sync use_cloud_models state."""
        self.state.tab_index = tab_index
        self.state.use_cloud_models = tab_index == 0

    def generate_code(self):
        """Generate VTK code from user query."""
        self._generate_and_execute_code()

    def clear_scene(self):
        """Clear the VTK scene and restore default axes."""
        try:
            self.renderer.RemoveAllViewProps()
            self._add_default_scene()
            self.renderer.ResetCamera()
            self.render_window.Render()
            self.ctrl.view_update()
        except Exception as e:
            print(f"Error clearing scene: {e}")

    def reset_camera(self):
        """Reset camera view."""
        try:
            self.renderer.ResetCamera()
            self.render_window.Render()
            self.ctrl.view_update()
        except Exception as e:
            print(f"Error resetting camera: {e}")

    def _generate_and_execute_code(self):
        """Generate VTK code using Anthropic API and execute it."""
        if not self.state.query_text.strip():
            self.state.error_message = "Please enter a query"
            return

        self.state.is_loading = True
        self.state.error_message = ""

        try:
            # Generate code using prompt functionality - reuse existing methods
            post_prompt = get_ui_post_prompt()
            enhanced_query = post_prompt + self.state.query_text

            # Reinitialize client with current settings
            self._init_prompt_client()
            if hasattr(self.state, "error_message") and self.state.error_message:
                return

            result = self.prompt_client.query(
                enhanced_query,
                api_key=self._get_api_key(),
                model=self._get_model(),
                base_url=self._get_base_url(),
                max_tokens=int(self.state.max_tokens),
                temperature=float(self.state.temperature),
                top_k=int(self.state.top_k),
                rag=self.state.use_rag,
                retry_attempts=int(self.state.retry_attempts),
            )

            # Handle both code and usage information
            if isinstance(result, tuple) and len(result) == 2:
                generated_code, usage = result
                if usage:
                    self.state.input_tokens = usage.prompt_tokens
                    self.state.output_tokens = usage.completion_tokens
            else:
                generated_code = result
                # Reset token counts if no usage info
                self.state.input_tokens = 0
                self.state.output_tokens = 0

            self.state.generated_code = EXPLAIN_RENDERER + "\n" + generated_code

            # Execute the generated code using the existing run_code method
            # But we need to modify it to work with our renderer
            self._execute_with_renderer(generated_code)

        except ValueError as e:
            if "max_tokens" in str(e):
                self.state.error_message = f"{str(e)} Current: {self.state.max_tokens}. Try increasing max tokens."
            else:
                self.state.error_message = f"Error generating code: {str(e)}"
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

            # Use the pre-initialized interactor
            # No need to create a new one

            exec(code_segment, exec_globals, {})

            # Reset camera and update view safely
            try:
                self.renderer.ResetCamera()
                self.render_window.Render()
                self.ctrl.view_update()
            except Exception as render_error:
                print(f"Render error: {render_error}")
                # Still update the view even if render fails
                self.ctrl.view_update()

        except Exception as e:
            self.state.error_message = f"Error executing code: {str(e)}"

    def _build_ui(self):
        """Build a simplified Vuetify UI."""
        # Initialize drawer state as collapsed
        self.state.main_drawer = True

        with SinglePageWithDrawerLayout(self.server) as layout:
            layout.title.set_text("VTK Prompt UI")
            with layout.toolbar:
                vuetify.VSpacer()
                # Token usage display
                with vuetify.VChip(
                    small=True,
                    color="primary",
                    text_color="white",
                    v_show="input_tokens > 0 || output_tokens > 0",
                    style="margin-right: 8px;",
                ):
                    html.Span(
                        "Tokens: In: {{ input_tokens }} | Out: {{ output_tokens }}"
                    )

                # VTK control buttons
                with vuetify.VBtn(
                    click=self.clear_scene,
                    icon=True,
                    v_tooltip_bottom="Clear Scene",
                ):
                    vuetify.VIcon("mdi-reload")
                with vuetify.VBtn(
                    click=self.reset_camera,
                    icon=True,
                    v_tooltip_bottom="Reset Camera",
                ):
                    vuetify.VIcon("mdi-camera-retake-outline")

                vuetify.VSwitch(
                    v_model=("$vuetify.theme.dark"),
                    hide_details=True,
                    dense=True,
                    label="Dark Mode",
                )

            with layout.drawer as drawer:
                drawer.width = 350

                with vuetify.VContainer():
                    # Tab Navigation - Centered
                    with vuetify.VRow(justify="center"):
                        with vuetify.VCol(cols="auto"):
                            with vuetify.VTabs(
                                v_model=("tab_index", 0),
                                color="primary",
                                slider_color="primary",
                                change=(self.on_tab_change, "[$event]"),
                                centered=True,
                                grow=False,
                            ):
                                vuetify.VTab("☁️ Cloud")
                                vuetify.VTab("🏠Local")

                    # Tab Content
                    with vuetify.VTabsItems(v_model="tab_index"):
                        # Cloud Providers Tab Content
                        with vuetify.VTabItem():
                            with vuetify.VCard(flat=True, style="margin-top: 10px;"):
                                with vuetify.VCardText():
                                    # Provider selection
                                    vuetify.VSelect(
                                        label="Provider",
                                        v_model=("provider", "openai"),
                                        items=("available_providers", []),
                                        dense=True,
                                        outlined=True,
                                        prepend_icon="mdi-cloud",
                                    )

                                    # Model selection
                                    vuetify.VSelect(
                                        label="Model",
                                        v_model=("model", "gpt-4o"),
                                        items=("available_models[provider] || []",),
                                        dense=True,
                                        outlined=True,
                                        prepend_icon="mdi-brain",
                                    )

                                    # API Token
                                    vuetify.VTextField(
                                        label="API Token",
                                        v_model=("api_token", ""),
                                        placeholder="Enter your API token",
                                        type="password",
                                        dense=True,
                                        outlined=True,
                                        prepend_icon="mdi-key",
                                        hint="Required for cloud providers",
                                        persistent_hint=True,
                                    )

                        # Local Models Tab Content
                        with vuetify.VTabItem():
                            with vuetify.VCard(flat=True, style="margin-top: 10px;"):
                                with vuetify.VCardText():
                                    vuetify.VTextField(
                                        label="Base URL",
                                        v_model=(
                                            "local_base_url",
                                            "http://localhost:11434/v1",
                                        ),
                                        placeholder="http://localhost:11434/v1",
                                        dense=True,
                                        outlined=True,
                                        prepend_icon="mdi-server",
                                        hint="Ollama, LM Studio, etc.",
                                        persistent_hint=True,
                                    )

                                    vuetify.VTextField(
                                        label="Model Name",
                                        v_model=("local_model", "devstral"),
                                        placeholder="devstral",
                                        dense=True,
                                        outlined=True,
                                        prepend_icon="mdi-brain",
                                        hint="Model identifier",
                                        persistent_hint=True,
                                    )

                                    # Optional API Token for local
                                    vuetify.VTextField(
                                        label="API Token (Optional)",
                                        v_model=("api_token", "ollama"),
                                        placeholder="ollama",
                                        type="password",
                                        dense=True,
                                        outlined=True,
                                        prepend_icon="mdi-key",
                                        hint="Optional for local servers",
                                        persistent_hint=True,
                                    )

                    with vuetify.VCard(style="margin-top: 10px;"):
                        with vuetify.VCardTitle(style="padding-bottom: 0;"):
                            "⚙️  RAG settings"
                        with vuetify.VCardText():
                            vuetify.VCheckbox(
                                v_model=("use_rag", False),
                                label="RAG",
                                prepend_icon="mdi-bookshelf",
                            )
                            vuetify.VTextField(
                                label="Top K",
                                v_model=("top_k", 5),
                                type="number",
                                min=1,
                                max=15,
                                dense=True,
                                disabled=("!use_rag",),
                                outlined=True,
                                prepend_icon="mdi-chart-scatter-plot",
                            )

                    with vuetify.VCard(style="margin-top: 10px;"):
                        with vuetify.VCardTitle(style="padding-bottom: 0;"):
                            "⚙️ Generation Settings"
                        with vuetify.VCardText():
                            vuetify.VSlider(
                                label="Temperature",
                                v_model=("temperature", 0.1),
                                min=0.0,
                                max=1.0,
                                step=0.1,
                                thumb_label="always",
                                color="orange",
                                prepend_icon="mdi-thermometer",
                            )
                            vuetify.VTextField(
                                label="Max Tokens",
                                v_model=("max_tokens", 1000),
                                type="number",
                                dense=True,
                                outlined=True,
                                prepend_icon="mdi-format-text",
                            )
                            vuetify.VTextField(
                                label="Retry Attempts",
                                v_model=("retry_attempts", 1),
                                type="number",
                                min=1,
                                max=5,
                                dense=True,
                                outlined=True,
                                prepend_icon="mdi-repeat",
                            )

            with layout.content:
                with vuetify.VContainer(fluid=True, style="height: 100%;"):
                    with vuetify.VRow(style="height: 100%;"):
                        # Left column - Generated code view
                        with vuetify.VCol(cols=6, style="height: 100%;"):
                            with vuetify.VCard(style="height: 80%;"):
                                with vuetify.VCardTitle():
                                    "Generated Code"
                                with vuetify.VCardText(
                                    style="height: calc(100% - 48px); overflow: auto;"
                                ):
                                    vuetify.VTextarea(
                                        v_model=("generated_code", ""),
                                        readonly=True,
                                        solo=True,
                                        hide_details=True,
                                        no_resize=True,
                                        auto_grow=True,
                                        style=(
                                            "font-family: monospace; min-height: 200px; "
                                            "max-height: 80vh; overflow-y: auto;"
                                        ),
                                        placeholder="Generated VTK code will appear here...",
                                    )

                            with vuetify.VCard(style="height: 20%;"):
                                with vuetify.VCardText():
                                    # Error message
                                    vuetify.VAlert(
                                        "{{ error_message }}",
                                        type="error",
                                        v_show=("error_message", ""),
                                        dense=True,
                                    )

                        # Right column - VTK viewer and prompt
                        with vuetify.VCol(cols=6, style="height: 100%;"):
                            with vuetify.VRow(no_gutters=True, style="height: 100%;"):
                                # Top: VTK render view
                                with vuetify.VCol(cols=12, style="height: 60%;"):
                                    with vuetify.VCard(style="height: 100%;"):
                                        with vuetify.VCardTitle():
                                            "VTK Visualization"
                                        with vuetify.VCardText(
                                            style="height: calc(100% - 48px);"
                                        ):
                                            # VTK render window
                                            view = vtk_widgets.VtkRemoteView(
                                                self.render_window,
                                                ref="view",
                                                style="width: 100%; height: 100%;",
                                                interactor_settings=[
                                                    (
                                                        "SetInteractorStyle",
                                                        [
                                                            "vtkInteractorStyleTrackballCamera"
                                                        ],
                                                    ),
                                                ],
                                            )
                                            self.ctrl.view_update = view.update
                                            self.ctrl.view_reset_camera = (
                                                view.reset_camera
                                            )

                                            # Register custom controller methods
                                            self.ctrl.on_tab_change = self.on_tab_change

                                            # Ensure initial render
                                            view.update()

                                # Bottom: Prompt input
                                with vuetify.VCol(cols=12, style="height: 40%;"):
                                    with vuetify.VCard(style="height: 100%;"):
                                        with vuetify.VCardText():
                                            # Cloud models chip
                                            vuetify.VChip(
                                                "☁️ {{ provider }}/{{ model }}",
                                                small=True,
                                                color="blue",
                                                text_color="white",
                                                label=True,
                                                style="margin-bottom: 8px;",
                                                v_show="use_cloud_models",
                                            )
                                            # Local models chip
                                            vuetify.VChip(
                                                (
                                                    "🏠 {{ local_base_url.replace('http://', '')"
                                                    ".replace('https://', '') }}/{{ local_model }}"
                                                ),
                                                small=True,
                                                color="green",
                                                text_color="white",
                                                label=True,
                                                style="margin-bottom: 8px;",
                                                v_show="!use_cloud_models",
                                            )

                                            # Query input
                                            vuetify.VTextarea(
                                                label="Describe VTK visualization",
                                                v_model=("query_text", ""),
                                                rows=4,
                                                outlined=True,
                                                placeholder="e.g., Create a red sphere with lighting",
                                            )

                                            # Generate button
                                            vuetify.VBtn(
                                                "Generate Code",
                                                color="primary",
                                                block=True,
                                                loading=("is_loading", False),
                                                click=self.generate_code,
                                                style="margin-bottom: 8px;",
                                            )

    def start(self):
        """Start the trame server."""
        self.server.start()


def main():
    """Main entry point for the trame app."""

    print("VTK Prompt UI - Enter your API token in the application settings.")
    print("Supported providers: OpenAI, Anthropic, Google Gemini, NVIDIA NIM")
    print("For local Ollama, use custom base URL and model configuration.")

    # Create and start the app
    app = VTKPromptApp()
    app.start()


if __name__ == "__main__":
    main()
