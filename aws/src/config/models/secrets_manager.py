from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from config.models.base import BaseConfig

# Generated  — AWS Secrets Manager auto-generates a strong random value.
# Reference  — The secret already exists in AWS; CDK registers a reference only.
# PlainText  — A single string; value may contain ${VAR} tokens resolved at synth time.
# KeyValue   — A JSON object; each value may contain ${VAR} tokens.
VALID_TYPES = {"PlainText", "KeyValue", "Generated", "Reference"}

_VALUE_FREE_TYPES = {"Generated", "Reference"}
_VALUE_REQUIRED_TYPES = {"PlainText", "KeyValue"}

# Reference secrets are externally managed; these fields cannot be applied.
_REFERENCE_UNSUPPORTED_FIELDS = ("kms_key_arn", "replica_regions")

VALID_REMOVAL_POLICIES = {"DESTROY", "RETAIN", "SNAPSHOT"}


@dataclass
class GenerateConfig:
    """
    Controls the random value AWS Secrets Manager generates at deploy time.
    Only used when ``SecretConfig.type == "Generated"``.

    Fields:
        length:                    Password length. Minimum 8 (default 32).
        exclude_characters:        Characters to exclude from the generated value.
                                   Useful to prevent chars that break connection strings.
        exclude_punctuation:       If true, all punctuation is excluded. Overrides
                                   ``exclude_characters`` for punctuation symbols.
        include_space:             If true, spaces may appear in the generated value.
        require_each_included_type: If true, the result must include at least one
                                   uppercase letter, one lowercase letter, one digit,
                                   and one non-excluded symbol.
        secret_string_template:    JSON template string for the non-generated part of
                                   the secret, e.g. ``'{"username": "admin"}'``.
                                   Must be used together with ``generate_string_key``.
        generate_string_key:       The JSON key where the generated password is placed.
                                   Required when ``secret_string_template`` is set.
                                   Produces ``{"username":"admin","password":"<gen>"}``.
    """

    length: int = 32
    exclude_characters: str = ""
    exclude_punctuation: bool = False
    include_space: bool = False
    require_each_included_type: bool = False
    secret_string_template: str = ""
    generate_string_key: str = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.length < 8:
            raise ValueError(f"'generate.length' must be at least 8. Got: {self.length}")
        has_template = bool(self.secret_string_template)
        has_key = bool(self.generate_string_key)
        if has_template != has_key:
            raise ValueError(
                "'generate.secret_string_template' and 'generate.generate_string_key' "
                "must both be specified or both omitted."
            )


@dataclass
class SecretConfig:
    """
    Encapsulates configuration for a single AWS Secrets Manager secret.

    Four storage strategies are supported:

    - Generated:  AWS auto-generates a cryptographically strong value at deploy
                  time using ``generate_secret_string``. No value in config.
    - Reference:  The secret pre-exists in AWS (created manually or by another
                  tool). CDK creates an ISecret reference only. No value in config.
                  ``kms_key_arn`` and ``replica_regions`` are not applicable.
    - PlainText:  A single string value. May use ``${VAR}`` tokens resolved from
                  environment variables at synth time.
    - KeyValue:   A JSON object. Each dict value may use ``${VAR}`` tokens.

    Fields:
        name:             Secret name/path — must start with '/'.
        type:             One of the four strategies above.
        description:      Free-text description shown in the AWS console.
        value:            String or mapping; required for PlainText and KeyValue.
        generate_config:  Random value settings; required for Generated.
        tags:             Key/value tags applied to the secret resource.
        removal_policy:   What happens when the stack is destroyed.
                          'DESTROY' (default) deletes the secret.
                          'RETAIN' keeps it after stack deletion — recommended for production.
                          'SNAPSHOT' schedules deletion with a 7-day recovery window.
        kms_key_arn:      ARN of a customer-managed KMS key for at-rest encryption.
                          Omit to use the AWS-managed key (free but less control).
                          Not applicable for Reference type.
        replica_regions:  List of AWS regions to replicate the secret into.
                          Not applicable for Reference type.
    """

    name: str
    type: str
    description: str = ""
    value: Optional[Union[str, dict]] = None
    generate_config: Optional[GenerateConfig] = None
    tags: dict[str, str] = field(default_factory=dict)
    removal_policy: str = "DESTROY"
    kms_key_arn: str = ""
    replica_regions: list[str] = field(default_factory=list)

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
        if self.removal_policy not in VALID_REMOVAL_POLICIES:
            raise ValueError(
                f"Secret '{self.name}' 'removal_policy' must be one of "
                f"{VALID_REMOVAL_POLICIES}. Got: '{self.removal_policy}'"
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
        if self.type == "Reference":
            if self.kms_key_arn:
                raise ValueError(
                    f"Secret '{self.name}' has type Reference — 'kms_key_arn' cannot be set "
                    f"on externally managed secrets."
                )
            if self.replica_regions:
                raise ValueError(
                    f"Secret '{self.name}' has type Reference — 'replica_regions' cannot be set "
                    f"on externally managed secrets."
                )

    @property
    def construct_id(self) -> str:
        """Returns a safe CDK construct ID derived from the secret name."""
        return self.name.lstrip("/").replace("/", "-")


@dataclass
class SecretsManagerConfig(BaseConfig):
    """
    Top-level config for the Secrets Manager stack.
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
    def from_dict(cls, project: str, environment: str, region: str, raw: dict) -> "SecretsManagerConfig":
        raw_secrets = raw.get("secrets", [])
        secrets = []
        for s in raw_secrets:
            raw_generate = s.get("generate")
            generate_config = (
                GenerateConfig(
                    length=raw_generate.get("length", 32),
                    exclude_characters=raw_generate.get("exclude_characters", ""),
                    exclude_punctuation=raw_generate.get("exclude_punctuation", False),
                    include_space=raw_generate.get("include_space", False),
                    require_each_included_type=raw_generate.get(
                        "require_each_included_type", False
                    ),
                    secret_string_template=raw_generate.get("secret_string_template", ""),
                    generate_string_key=raw_generate.get("generate_string_key", ""),
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
                    tags=s.get("tags", {}),
                    removal_policy=s.get("removal_policy", "DESTROY"),
                    kms_key_arn=s.get("kms_key_arn", ""),
                    replica_regions=s.get("replica_regions", []),
                )
            )
        return cls(project=project, environment=environment, region=region, secrets=secrets)
