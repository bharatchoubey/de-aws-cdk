from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from .base import BaseConfig

# SecureString is intentionally excluded — secrets and credentials must be
# stored in AWS Secrets Manager, not SSM Parameter Store.
VALID_TYPES = {"String", "StringList"}
VALID_TIERS = {"Standard", "Advanced"}


@dataclass
class SsmParameterConfig:
    """
    Encapsulates configuration for a single SSM Parameter Store entry.

    Only non-sensitive configuration values belong here (String, StringList).
    For secrets and credentials use AWS Secrets Manager instead.

    Validation is strict: unknown types or tiers raise immediately so
    CDK synthesis never proceeds with a bad config.
    """

    name: str
    type: str
    value: Union[str, list]
    description: str = ""
    tier: str = "Standard"

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name or not self.name.startswith("/"):
            raise ValueError(
                f"SSM parameter 'name' must be a non-empty string starting with '/'. Got: '{self.name}'"
            )
        if self.type not in VALID_TYPES:
            raise ValueError(
                f"SSM parameter 'type' must be one of {VALID_TYPES}. Got: '{self.type}'. "
                f"Tip: use AWS Secrets Manager for sensitive values."
            )
        if self.tier not in VALID_TIERS:
            raise ValueError(
                f"SSM parameter 'tier' must be one of {VALID_TIERS}. Got: '{self.tier}'"
            )
        if self.type == "StringList" and not isinstance(self.value, list):
            raise ValueError(
                f"SSM parameter '{self.name}' has type StringList but 'value' is not a list."
            )
        if self.type == "String" and not isinstance(self.value, str):
            raise ValueError(
                f"SSM parameter '{self.name}' has type String but 'value' is not a string."
            )

    @property
    def construct_id(self) -> str:
        """Returns a safe CDK construct ID derived from the parameter name."""
        return self.name.lstrip("/").replace("/", "-")


@dataclass
class SsmConfig(BaseConfig):
    """
    Top-level config for the SSM stack.

    Holds the flat list of SsmParameterConfig objects parsed from
    the YAML 'ssm.parameters' block.
    """

    parameters: list[SsmParameterConfig] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        if not self.parameters:
            raise ValueError("'ssm.parameters' must contain at least one entry.")
        for param in self.parameters:
            param.validate()

    @classmethod
    def from_dict(cls, environment: str, region: str, raw: dict) -> "SsmConfig":
        """
        Factory — builds a fully validated SsmConfig from the parsed YAML dict.

        Args:
            environment: resolved environment name (e.g. 'dev')
            region: AWS region string
            raw: the 'ssm' block from the YAML file

        Returns:
            Validated SsmConfig instance
        """
        raw_params = raw.get("parameters", [])
        parameters = [
            SsmParameterConfig(
                name=p["name"],
                type=p["type"],
                value=p["value"],
                description=p.get("description", ""),
                tier=p.get("tier", "Standard"),
            )
            for p in raw_params
        ]
        return cls(environment=environment, region=region, parameters=parameters)
