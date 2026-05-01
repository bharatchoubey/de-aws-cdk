from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from config.models.base import BaseConfig

# Generated  — AWS Secrets Manager auto-generates a strong random value.
# Reference  — The secret already exists in AWS; CDK registers a reference only.
# PlainText  — A single string; value may contain ${VAR} tokens resolved at synth time.
# KeyValue   — A JSON object; each value may contain ${VAR} tokens.
VALID_TYPES = {"PlainText", "KeyValue", "Generated", "Reference"}

# Types that must NOT carry a value in config (value comes from AWS or env)
_VALUE_FREE_TYPES = {"Generated", "Reference"}

# Types that require a value
_VALUE_REQUIRED_TYPES = {"PlainText", "KeyValue"}


@dataclass
class GenerateConfig:
    """
    Controls the random value AWS Secrets Manager generates at deploy time.
    Only used when ``SecretConfig.type == "Generated"``.
    """

    length: int = 32
    exclude_characters: str = ""
    exclude_punctuation: bool = False

    def __post_init__(self) -> None:
        if self.length < 8:
            raise ValueError(f"'generate.length' must be at least 8. Got: {self.length}")


@dataclass
class SecretConfig:
    """
    Encapsulates configuration for a single AWS Secrets Manager secret.

    Four storage strategies are supported:

    - Generated:  AWS auto-generates a cryptographically strong value at deploy
                  time using ``generate_secret_string``. No value in config.
    - Reference:  The secret pre-exists in AWS (created manually or by another
                  tool). CDK creates an ISecret reference only. No value in config.
    - PlainText:  A single string value. May use ``${VAR}`` tokens resolved from
                  environment variables at synth time.
    - KeyValue:   A JSON object. Each dict value may use ``${VAR}`` tokens.

    Validation is strict — type mismatches and missing required fields raise
    immediately so CDK synthesis never proceeds with a malformed config.
    """

    name: str
    type: str
    description: str = ""
    value: Optional[Union[str, dict]] = None
    generate_config: Optional[GenerateConfig] = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name or not self.name.startswith("/"):
            raise ValueError(
                f"Secret 'name' must be a non-empty string starting with '/'. Got: '{self.name}'"
            )
        if self.type not in VALID_TYPES:
            raise ValueError(
                f"Secret 'type' must be one of {VALID_TYPES}. Got: '{self.type}'"
            )
        if self.type in _VALUE_FREE_TYPES and self.value is not None:
            raise ValueError(
                f"Secret '{self.name}' has type '{self.type}' and must not have a 'value' field. "
                f"The value is managed by AWS or provided externally."
            )
        if self.type in _VALUE_REQUIRED_TYPES and self.value is None:
            raise ValueError(
                f"Secret '{self.name}' has type '{self.type}' and requires a 'value' field. "
                f"Use ${{VAR}} syntax to inject from environment variables."
            )
        if self.type == "PlainText" and not isinstance(self.value, str):
            raise ValueError(
                f"Secret '{self.name}' has type PlainText but 'value' is not a string."
            )
        if self.type == "KeyValue" and not isinstance(self.value, dict):
            raise ValueError(
                f"Secret '{self.name}' has type KeyValue but 'value' is not a mapping."
            )
        if self.type == "KeyValue" and not self.value:
            raise ValueError(
                f"Secret '{self.name}' has type KeyValue but 'value' is an empty mapping."
            )
        if self.type == "Generated" and self.generate_config is None:
            raise ValueError(
                f"Secret '{self.name}' has type Generated but is missing the 'generate' block."
            )

    @property
    def construct_id(self) -> str:
        """Returns a safe CDK construct ID derived from the secret name."""
        return self.name.lstrip("/").replace("/", "-")


@dataclass
class SecretsManagerConfig(BaseConfig):
    """
    Top-level config for the Secrets Manager stack.

    Holds the flat list of SecretConfig objects parsed from the
    YAML 'secrets_manager.secrets' block.
    """

    secrets: list[SecretConfig] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        if not self.secrets:
            raise ValueError("'secrets_manager.secrets' must contain at least one entry.")
        names = [s.name for s in self.secrets]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate secret names found: {duplicates}. Each secret name must be unique."
            )
        for secret in self.secrets:
            secret.validate()

    @classmethod
    def from_dict(cls, environment: str, region: str, raw: dict) -> "SecretsManagerConfig":
        """
        Factory — builds a fully validated SecretsManagerConfig from the parsed YAML dict.

        Args:
            environment: resolved environment name (e.g. 'dev')
            region: AWS region string
            raw: the 'secrets_manager' block from the YAML file

        Returns:
            Validated SecretsManagerConfig instance
        """
        raw_secrets = raw.get("secrets", [])
        secrets = []
        for s in raw_secrets:
            raw_generate = s.get("generate")
            generate_config = (
                GenerateConfig(
                    length=raw_generate.get("length", 32),
                    exclude_characters=raw_generate.get("exclude_characters", ""),
                    exclude_punctuation=raw_generate.get("exclude_punctuation", False),
                )
                if raw_generate is not None
                else None
            )
            secrets.append(
                SecretConfig(
                    name=s["name"],
                    type=s["type"],
                    description=s.get("description", ""),
                    value=s.get("value"),
                    generate_config=generate_config,
                )
            )
        return cls(environment=environment, region=region, secrets=secrets)
