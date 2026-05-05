from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from .base import BaseConfig

# SecureString is intentionally excluded — secrets and credentials must be
# stored in AWS Secrets Manager, not SSM Parameter Store.
VALID_TYPES = {"String", "StringList"}
VALID_TIERS = {"Standard", "Advanced"}

# String-only: StringList does not support allowed_pattern or data_type.
# aws:ec2:image causes AWS to validate the value is a valid AMI ID.
VALID_DATA_TYPES = {"text", "aws:ec2:image"}


@dataclass
class SsmParameterConfig:
    """
    Encapsulates configuration for a single SSM Parameter Store entry.

    Only non-sensitive configuration values belong here (String, StringList).
    For secrets and credentials use AWS Secrets Manager instead.

    Validation is strict: unknown types or tiers raise immediately so
    CDK synthesis never proceeds with a bad config.

    Fields:
        name:            Parameter path — must start with '/'.
        type:            'String' or 'StringList'.
        value:           String scalar or YAML list (for StringList).
        description:     Free-text description shown in the AWS console.
        tier:            'Standard' (default) or 'Advanced'.
        tags:            Key/value tags applied to the parameter resource.
        allowed_pattern: Regex the value must match at creation time.
                         Only valid for String parameters.
        data_type:       'text' (default) or 'aws:ec2:image'.
                         Use 'aws:ec2:image' so AWS validates and resolves
                         AMI IDs automatically. Only valid for String parameters.
    """

    name: str
    type: str
    value: Union[str, list]
    description: str = ""
    tier: str = "Standard"
    tags: dict[str, str] = field(default_factory=dict)
    allowed_pattern: str = ""
    data_type: str = "text"

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
        if self.type == "StringList" and self.allowed_pattern:
            raise ValueError(
                f"SSM parameter '{self.name}': 'allowed_pattern' is only supported for "
                f"String parameters, not StringList."
            )
        if self.type == "StringList" and self.data_type != "text":
            raise ValueError(
                f"SSM parameter '{self.name}': 'data_type' is only supported for "
                f"String parameters, not StringList."
            )
        if self.data_type not in VALID_DATA_TYPES:
            raise ValueError(
                f"SSM parameter '{self.name}' 'data_type' must be one of "
                f"{VALID_DATA_TYPES}. Got: '{self.data_type}'"
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
    def from_dict(cls, project: str, environment: str, region: str, raw: dict) -> "SsmConfig":
        raw_params = raw.get("parameters", [])
        parameters = [
            SsmParameterConfig(
                name=p["name"],
                type=p["type"],
                value=p["value"],
                description=p.get("description", ""),
                tier=p.get("tier", "Standard"),
                tags=p.get("tags", {}),
                allowed_pattern=p.get("allowed_pattern", ""),
                data_type=p.get("data_type", "text"),
            )
            for p in raw_params
        ]
        return cls(project=project, environment=environment, region=region, parameters=parameters)
