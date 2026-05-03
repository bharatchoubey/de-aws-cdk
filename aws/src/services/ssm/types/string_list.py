from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_ssm as ssm
from constructs import Construct

from config.models.ssm import SsmParameterConfig
from services.ssm.types.base import BaseSsmParameter


class StringListParameter(BaseSsmParameter):
    """
    Creates an SSM Parameter Store entry of type StringList (L2 construct).

    A StringList is stored as a comma-separated string in SSM and returned as
    a list by the AWS SDK.  It does not support ``allowed_pattern`` or
    ``data_type`` — those are String-only features validated at the config
    model level.

    Supports:
      - ``tags``: key/value pairs applied to the underlying CloudFormation resource.
    """

    def create(self, scope: Construct, config: SsmParameterConfig) -> None:
        param = ssm.StringListParameter(
            scope,
            "Resource",
            parameter_name=config.name,
            string_list_value=config.value,
            description=config.description or None,
            tier=self._resolve_tier(config.tier),
        )
        for key, value in config.tags.items():
            cdk.Tags.of(param).add(key, value)

    @staticmethod
    def _resolve_tier(tier: str) -> ssm.ParameterTier:
        return ssm.ParameterTier.ADVANCED if tier == "Advanced" else ssm.ParameterTier.STANDARD
