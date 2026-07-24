from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    ai_provider: str
    openai_api_key: str
    openai_model: str
    ai_max_output_tokens: int
    ai_request_timeout: float
    ai_max_retries: int

    @classmethod
    def from_environment(cls) -> "Settings":
        """
        Build application settings from environment variables.
        """

        settings = cls(
            ai_provider=os.getenv(
                "AI_PROVIDER",
                "openai",
            ).strip().lower(),
            openai_api_key=os.getenv(
                "OPENAI_API_KEY",
                "",
            ).strip(),
            openai_model=os.getenv(
                "OPENAI_MODEL",
                "gpt-5.6",
            ).strip(),
            ai_max_output_tokens=_read_positive_integer(
                variable_name="AI_MAX_OUTPUT_TOKENS",
                default=6000,
            ),
            ai_request_timeout=_read_positive_float(
                variable_name="AI_REQUEST_TIMEOUT",
                default=120.0,
            ),
            ai_max_retries=_read_non_negative_integer(
                variable_name="AI_MAX_RETRIES",
                default=3,
            ),
        )

        settings.validate()

        return settings

    def validate(self) -> None:
        """
        Validate configuration required by the selected AI provider.
        """

        supported_providers = {
            "openai",
        }

        if self.ai_provider not in supported_providers:
            raise ConfigurationError(
                "Unsupported AI provider: "
                f"{self.ai_provider}. "
                f"Supported providers: "
                f"{', '.join(sorted(supported_providers))}"
            )

        if self.ai_provider == "openai":
            if not self.openai_api_key:
                raise ConfigurationError(
                    "OPENAI_API_KEY is missing. "
                    "Add it to the project .env file."
                )

            if self.openai_api_key == (
                "your_openai_api_key_here"
            ):
                raise ConfigurationError(
                    "OPENAI_API_KEY still contains "
                    "the placeholder value."
                )

        if not self.openai_model:
            raise ConfigurationError(
                "OPENAI_MODEL cannot be empty."
            )


def _read_positive_integer(
    variable_name: str,
    default: int,
) -> int:
    raw_value = os.getenv(
        variable_name,
        str(default),
    )

    try:
        value = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(
            f"{variable_name} must be an integer."
        ) from error

    if value <= 0:
        raise ConfigurationError(
            f"{variable_name} must be greater than zero."
        )

    return value


def _read_non_negative_integer(
    variable_name: str,
    default: int,
) -> int:
    raw_value = os.getenv(
        variable_name,
        str(default),
    )

    try:
        value = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(
            f"{variable_name} must be an integer."
        ) from error

    if value < 0:
        raise ConfigurationError(
            f"{variable_name} cannot be negative."
        )

    return value


def _read_positive_float(
    variable_name: str,
    default: float,
) -> float:
    raw_value = os.getenv(
        variable_name,
        str(default),
    )

    try:
        value = float(raw_value)
    except ValueError as error:
        raise ConfigurationError(
            f"{variable_name} must be numeric."
        ) from error

    if value <= 0:
        raise ConfigurationError(
            f"{variable_name} must be greater than zero."
        )

    return value


def get_settings() -> Settings:
    """
    Return validated application settings.
    """

    return Settings.from_environment()