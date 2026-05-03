from __future__ import annotations

from constructs import Construct

from config.models.secrets_manager import SecretConfig
from logger import get_logger
from services.base import BaseServiceConstruct
from services.secrets_manager.types.base import BaseSecretType
from services.secrets_manager.types.generated import GeneratedSecret
from services.secrets_manager.types.key_value import KeyValueSecret
from services.secrets_manager.types.plain_text import PlainTextSecret
from services.secrets_manager.types.reference import ReferenceSecret

log = get_logger(__name__)

_HANDLERS: dict[str, BaseSecretType] = {
    "PlainText": PlainTextSecret(),
    "KeyValue": KeyValueSecret(),
    "Generated": GeneratedSecret(),
    "Reference": ReferenceSecret(),
}


class SecretConstruct(BaseServiceConstruct):
    """
    CDK Construct for a single AWS Secrets Manager secret.

    Delegates the actual CDK resource creation to the appropriate
    ``BaseSecretType`` strategy, selected by ``config.type`` at runtime.
    The handler registry (``_HANDLERS``) is the only place that needs to
    change when a new secret strategy is added.

    Supported strategies:
      - PlainText:  single string; supports ``${VAR}`` env var tokens.
      - KeyValue:   JSON object; each value supports ``${VAR}`` tokens.
      - Generated:  AWS auto-generates a strong random value at deploy time.
      - Reference:  registers an ISecret reference to a pre-existing secret.

    Inherits from ``BaseServiceConstruct`` which guarantees
    ``_create_resource()`` is called automatically during construction.
    """

    def __init__(self, scope: Construct, config: SecretConfig) -> None:
        super().__init__(scope, config.construct_id, config)

    def _create_resource(self) -> None:
        try:
            handler = self._resolve_handler()
            log.debug("Using handler '%s' for secret '%s'", type(handler).__name__, self._config.name)
            handler.create(self, self._config)
            log.debug("Secret created: name=%s type=%s", self._config.name, self._config.type)
        except (ValueError, EnvironmentError):
            raise
        except Exception as exc:
            log.error("Unexpected error creating secret '%s': %s", self._config.name, exc)
            raise

    def _resolve_handler(self) -> BaseSecretType:
        handler = _HANDLERS.get(self._config.type)
        if handler is None:
            supported = ", ".join(sorted(_HANDLERS))
            raise ValueError(
                f"Unsupported secret type: '{self._config.type}'. "
                f"Supported types: [{supported}]"
            )
        return handler
