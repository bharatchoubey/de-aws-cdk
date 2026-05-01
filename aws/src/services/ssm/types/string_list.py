from __future__ import annotations

import aws_cdk.aws_ssm as ssm
from constructs import Construct

from config.models.ssm import SsmParameterConfig
from services.ssm.types.base import BaseSsmParameter


class StringListParameter(BaseSsmParameter):
    """Creates an SSM Parameter Store entry of type StringList (L2 construct)."""

    def create(self, scope: Construct, config: SsmParameterConfig) -> None:
        ssm.StringListParameter(
            scope,
            "Resource",
            parameter_name=config.name,
            string_list_value=config.value,
            description=config.description or None,
            tier=self._resolve_tier(config.tier),
        )

    @staticmethod
    def _resolve_tier(tier: str) -> ssm.ParameterTier:
        return ssm.ParameterTier.ADVANCED if tier == "Advanced" else ssm.ParameterTier.STANDARD
