import json  # noqa: D100

from jinja2 import Environment, StrictUndefined, TemplateError, TemplateSyntaxError, UndefinedError
from langflow.custom.custom_component.component import Component
from langflow.io import DropdownInput, MessageInput, MultilineInput, Output
from langflow.schema import Data, Message


class JinjaTemplateRenderer(Component):  # noqa: D101
    display_name = "Jinja2 Template Renderer"
    description = "Uses Jinja2 to render templates with provided variables. Supports both plain text and JSON outputs."
    documentation: str = "https://docs.langflow.org/components-custom-components"
    icon = "code"
    name = "JinjaTemplateRenderer"

    inputs = [
        MessageInput(
            name="input_message",
            display_name="Input Message Bypass",
            info="The input message to bypass the component. This is optional and can be used to pass additional context.",  # noqa: E501
            required=False,
        ),
        MultilineInput(
            name="template",
            display_name="Jinja2 Template",
            info="The Jinja2 template string to render.",
            required=True,
            value="{{ greeting }}, {{ name }}!",
        ),
        MultilineInput(
            name="template_variables",
            display_name="Template Variables (JSON)",
            info="JSON string representing variables to render the template with.",
            required=False,
            value='{"greeting": "Hello", "name": "World"}',
        ),
        DropdownInput(
            name="output_type",
            display_name="Output Type",
            options=["Plain Text", "JSON"],
            value="Plain Text",
            info="Select the output format: Plain Text returns a Message, JSON returns a Data object.",
        ),
    ]

    outputs = [
        Output(
            display_name="Rendered Output",
            name="rendered_output",
            method="render_output",
        ),
    ]

    def render_output(self) -> Message:
        """Renders a Jinja2 template using provided template variables and returns the output.

        The method performs the following steps:
        1. Parses `self.template_variables` as a JSON dictionary.
        2. Sets up a Jinja2 environment with strict undefined variables and autoescaping.
        3. Renders the template with the parsed variables.
        4. Returns the output as either a JSON object (if `self.output_type` is "JSON") or plain text.

        Returns:
            Message or Data: The rendered output wrapped in a Message (plain text) or Data (JSON) object.

        Raises:
            ValueError: If template variables are not a valid JSON object, if template rendering fails,
                        or if the rendered output is not valid JSON when JSON output is requested.
        """
        # Parse template_variables input as JSON dict
        try:
            variables_dict = json.loads(self.template_variables) if self.template_variables else {}
            if not isinstance(variables_dict, dict):
                msg = "Template variables input must be a JSON object (dictionary)."
                raise ValueError(msg)  # noqa: TRY004
        except json.JSONDecodeError as e:
            msg = f"Error parsing template variables JSON: {e}"
            raise ValueError(msg) from e

        # Setup Jinja2 environment with strict undefined to catch errors
        env = Environment(undefined=StrictUndefined, autoescape=True)

        try:
            template = env.from_string(self.template)
            rendered = template.render(**variables_dict)
        except (TemplateSyntaxError, UndefinedError, TemplateError) as e:
            msg = f"Template rendering error: {e}"
            raise ValueError(msg) from e

        # Return output based on selected output_type
        if self.output_type == "JSON":
            try:
                parsed_json = json.loads(rendered)
                data_obj = Data(value=parsed_json)
                self.status = "Rendered JSON output successfully."
                return data_obj  # noqa: TRY300
            except json.JSONDecodeError as e:
                msg = f"Rendered output is not valid JSON: {e}"
                raise ValueError(msg) from e
        else:
            # Plain Text output as Message
            msg = Message(text=rendered)
            self.status = "Rendered plain text output successfully."
            return msg
