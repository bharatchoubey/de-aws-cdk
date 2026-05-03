from __future__ import annotations

from constructs import Construct

from config.models.ssm import SsmParameterConfig
from logger import get_logger
from services.base import BaseServiceConstruct
from services.ssm.types.base import BaseSsmParameter
from services.ssm.types.string import StringParameter
from services.ssm.types.string_list import StringListParameter

log = get_logger(__name__)

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

    def __init__(self, scope: Construct, config: SsmParameterConfig, name_prefix: str = "") -> None:
        cid = f"{name_prefix}-{config.construct_id}" if name_prefix else config.construct_id
        super().__init__(scope, cid, config)

    def _create_resource(self) -> None:
        try:
            handler = self._resolve_handler()
            log.debug("Using handler '%s' for parameter '%s'", type(handler).__name__, self._config.name)
            handler.create(self, self._config)
            log.debug("SSM parameter created: name=%s type=%s", self._config.name, self._config.type)
        except ValueError:
            raise
        except Exception as exc:
            log.error("Unexpected error creating SSM parameter '%s': %s", self._config.name, exc)
            raise

    def _resolve_handler(self) -> BaseSsmParameter:
        handler = _HANDLERS.get(self._config.type)
        if handler is None:
            supported = ", ".join(sorted(_HANDLERS))
            raise ValueError(
                f"Unsupported SSM parameter type: '{self._config.type}'. "
                f"Supported types: [{supported}]"
            )
        return handler
