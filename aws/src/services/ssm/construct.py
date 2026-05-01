from __future__ import annotations

from constructs import Construct

from config.models.ssm import SsmParameterConfig
from services.base import BaseServiceConstruct
from services.ssm.types.base import BaseSsmParameter
from services.ssm.types.string import StringParameter
from services.ssm.types.string_list import StringListParameter

# SecureString is intentionally absent — secrets belong in AWS Secrets Manager.
_HANDLERS: dict[str, BaseSsmParameter] = {
    "String": StringParameter(),
    "StringList": StringListParameter(),
}


class SsmParameterConstruct(BaseServiceConstruct):
    """
    CDK Construct for a single SSM Parameter Store parameter.

    Delegates the actual CDK resource creation to the appropriate
    ``BaseSsmParameter`` strategy, selected by ``config.type`` at runtime.
    The handler registry (``_HANDLERS``) is the only place that needs to
    change when a new parameter type is added.

    Inherits from ``BaseServiceConstruct`` which guarantees
    ``_create_resource()`` is called automatically during construction.
    """

    def __init__(self, scope: Construct, config: SsmParameterConfig) -> None:
        super().__init__(scope, config.construct_id, config)

    def _create_resource(self) -> None:
        handler = self._resolve_handler()
        handler.create(self, self._config)

    def _resolve_handler(self) -> BaseSsmParameter:
        handler = _HANDLERS.get(self._config.type)
        if handler is None:
            supported = ", ".join(sorted(_HANDLERS))
            raise ValueError(
                f"Unsupported SSM parameter type: '{self._config.type}'. "
                f"Supported types: [{supported}]"
            )
        return handler
