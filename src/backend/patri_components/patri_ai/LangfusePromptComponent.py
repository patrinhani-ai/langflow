import re  # noqa: D100, N999
from typing import Any

from langchain_core.prompts import HumanMessagePromptTemplate, PromptTemplate
from langflow.custom import Component
from langflow.inputs import DefaultPromptField, StrInput
from langflow.io import Output
from langflow.schema import dotdict
from langflow.schema.message import Message


class LangfusePromptComponent(Component):  # noqa: D101
    display_name: str = "Langfuse Prompt"
    description: str = "Prompt Component that uses Langfuse prompts"
    icon = "prompts"
    trace_type = "prompt"
    name = "LangfusePromptComponent"

    inputs = [
        StrInput(
            name="langfuse_prompt_key",
            display_name="Langfuse Prompt Key",
            info="The Langfuse prompt to use, i.e., 'prompt-key'",
            refresh_button=True,
            refresh_button_text="Fetch Prompt",
            real_time_refresh=True,
            required=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Output Prompt", name="prompt", method="build_prompt"),
    ]

    def update_build_config(  # noqa: D102
        self,
        build_config: dotdict,
        field_value: Any,
        field_name: str | None = None,
    ):
        # If the field is not langfuse_prompt_key or the value is empty, return the build config as is
        if field_name != "langfuse_prompt_key" or not field_value:
            return build_config

        # Fetch the template
        template = self._fetch_langfuse_template()

        # Get the template's messages
        if hasattr(template, "messages"):
            template_messages = template.messages
        else:
            template_messages = [HumanMessagePromptTemplate(prompt=template)]

        # Extract the messages from the prompt data
        prompt_template = [message_data.prompt for message_data in template_messages]

        # Regular expression to find all instances of {<string>}
        pattern = r"\{(.*?)\}"

        # Get all the custom fields
        custom_fields: list[str] = []
        full_template = ""
        for message in prompt_template:
            # Find all matches
            matches = re.findall(pattern, message.template)
            custom_fields += matches

            # Create a string version of the full template
            full_template = full_template + "\n" + message.template

        # No need to reprocess if we have them already
        if all("param_" + custom_field in build_config for custom_field in custom_fields):
            return build_config

        # Easter egg: Show template in info popup
        build_config["langfuse_prompt_key"]["info"] = full_template

        # Remove old parameter inputs if any
        for key in build_config.copy():
            if key.startswith("param_"):
                del build_config[key]

        # Now create inputs for each
        for custom_field in custom_fields:
            new_parameter = DefaultPromptField(
                name=f"param_{custom_field}",
                display_name=custom_field,
                info="Fill in the value for {" + custom_field + "}",
            ).to_dict()

            # Add the new parameter to the build config
            build_config[f"param_{custom_field}"] = new_parameter

        return build_config

    async def build_prompt(  # noqa: D102
        self,
    ) -> Message:
        # Fetch the template
        template = self._fetch_langfuse_template()

        # Get the parameters from the attributes
        params_dict = {param: getattr(self, "param_" + param, f"{{{param}}}") for param in template.input_variables}
        original_params = {k: v.text if hasattr(v, "text") else v for k, v in params_dict.items() if v is not None}
        prompt_value = template.invoke(original_params)

        # Update the template with the new value
        original_params["template"] = prompt_value.to_string()

        # Now pass the filtered attributes to the function
        prompt = Message.from_template(**original_params, metadata={"langfuse_prompt": self.langfuse_prompt_key})

        self.status = prompt.text

        return prompt

    def _fetch_langfuse_template(self):
        from langfuse import Langfuse

        langfuse = Langfuse()

        langfuse_prompt = langfuse.get_prompt(self.langfuse_prompt_key, label="latest")

        langchain_prompt = langfuse_prompt.get_langchain_prompt()

        return PromptTemplate.from_template(langchain_prompt, metadata={"langfuse_prompt": langfuse_prompt})
