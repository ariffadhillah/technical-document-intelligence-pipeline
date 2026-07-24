from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from src.config.settings import Settings


SchemaType = TypeVar(
    "SchemaType",
    bound=BaseModel,
)


class OpenAIProviderError(RuntimeError):
    """
    Raised when OpenAI returns an unusable result.
    """


class OpenAIProvider:
    """
    Wrapper around the OpenAI client.

    All OpenAI communication should happen through
    this provider.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.ai_request_timeout,
            max_retries=settings.ai_max_retries,
        )

    def health_check(self) -> str:
        """
        Perform a minimal API connectivity test.
        """

        response = self.client.responses.create(
            model=self.settings.openai_model,
            input="Reply using exactly one word: READY",
            max_output_tokens=32,
        )

        result = response.output_text.strip()

        if not result:
            raise OpenAIProviderError(
                "OpenAI health check returned empty output."
            )

        return result

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[SchemaType],
    ) -> SchemaType:
        """
        Generate and validate structured output using
        a Pydantic schema.
        """

        if not system_prompt.strip():
            raise ValueError(
                "system_prompt cannot be empty."
            )

        if not user_prompt.strip():
            raise ValueError(
                "user_prompt cannot be empty."
            )

        response = self.client.responses.parse(
            model=self.settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            text_format=response_schema,
            max_output_tokens=(
                self.settings.ai_max_output_tokens
            ),
        )

        parsed_result = response.output_parsed

        if parsed_result is None:
            raise OpenAIProviderError(
                "OpenAI returned no parsed structured output."
            )

        return parsed_result