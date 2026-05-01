from __future__ import annotations

from constructs import Construct

from config.models.ssm import SsmConfig
from services.ssm.construct import SsmParameterConstruct
from stacks.base import BaseServiceStack


class SsmStack(BaseServiceStack):
    """
    CDK Stack for AWS SSM Parameter Store.

    Reads the list of parameters from ``SsmConfig`` and creates one
    ``SsmParameterConstruct`` per entry.  Each construct is responsible
    for its own CDK resource; this stack only orchestrates iteration.

    Stack ID: ``{env}-ssm-stack``  (e.g. ``dev-ssm-stack``)
    """

    def __init__(self, scope: Construct, config: SsmConfig, **kwargs) -> None:
        super().__init__(scope, "ssm", config, **kwargs)

    def _build(self) -> None:
        for param_config in self._config.parameters:
            SsmParameterConstruct(self, param_config)
