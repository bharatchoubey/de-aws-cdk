from __future__ import annotations

from constructs import Construct

from config.models.ssm import SsmConfig
from logger import get_logger
from services.ssm.construct import SsmParameterConstruct
from stacks.base import BaseServiceStack

log = get_logger(__name__)


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
        total = len(self._config.parameters)
        log.info("Building SSM stack: %d parameter(s) to provision", total)

        for param_config in self._config.parameters:
            log.debug("Creating SSM parameter: name=%s type=%s", param_config.name, param_config.type)
            try:
                SsmParameterConstruct(self, param_config)
            except Exception as exc:
                log.error("Failed to create SSM parameter '%s': %s", param_config.name, exc)
                raise

        log.info("SSM stack build complete: %d parameter(s) defined", total)
