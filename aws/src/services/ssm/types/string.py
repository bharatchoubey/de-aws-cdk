from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_ssm as ssm
from constructs import Construct

from config.models.ssm import SsmParameterConfig
from services.ssm.types.base import BaseSsmParameter


class StringParameter(BaseSsmParameter):
    """
    Creates an SSM Parameter Store entry of type String (L2 construct).

    Supports all String-specific fields:
      - ``allowed_pattern``: regex that the value must satisfy at creation time.
      - ``data_type``: 'text' (default) or 'aws:ec2:image' — the latter causes
        AWS to validate that the value is a real AMI ID in the current region.
      - ``tags``: key/value pairs applied to the underlying CloudFormation resource.
    """

    def create(self, scope: Construct, config: SsmParameterConfig) -> None:
        param = ssm.StringParameter(
            scope,
            "Resource",
            parameter_name=config.name,
            string_value=config.value,
            description=config.description or None,
            tier=self._resolve_tier(config.tier),
            allowed_pattern=config.allowed_pattern or None,
            data_type=self._resolve_data_type(config.data_type),
        )
        for key, value in config.tags.items():
            cdk.Tags.of(param).add(key, value)

    @staticmethod
    def _resolve_tier(tier: str) -> ssm.ParameterTier:
        return ssm.ParameterTier.ADVANCED if tier == "Advanced" else ssm.ParameterTier.STANDARD

    @staticmethod
    def _resolve_data_type(data_type: str) -> ssm.ParameterDataType:
        return (
            ssm.ParameterDataType.AWS_EC2_IMAGE
            if data_type == "aws:ec2:image"
            else ssm.ParameterDataType.TEXT
        )
