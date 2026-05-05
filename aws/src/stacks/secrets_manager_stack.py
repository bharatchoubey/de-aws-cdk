from __future__ import annotations

from constructs import Construct

from config.models.secrets_manager import SecretsManagerConfig
from logger import get_logger
from services.secrets_manager.construct import SecretConstruct
from stacks.base import BaseServiceStack

log = get_logger(__name__)


class SecretsManagerStack(BaseServiceStack):
    """
    CDK Stack for AWS Secrets Manager.

    Reads the list of secrets from ``SecretsManagerConfig`` and creates one
    ``SecretConstruct`` per entry.  Each construct is responsible for its own
    CDK resource; this stack only orchestrates iteration.

    Stack ID: ``{env}-secrets-manager-stack``  (e.g. ``dev-secrets-manager-stack``)
    """

    def __init__(self, scope: Construct, config: SecretsManagerConfig, **kwargs) -> None:
        super().__init__(scope, "secrets-manager", config, **kwargs)

    def _build(self) -> None:
        total = len(self._config.secrets)
        log.info("Building Secrets Manager stack: %d secret(s) to provision", total)

        for secret_config in self._config.secrets:
            log.debug("Creating secret: name=%s type=%s", secret_config.name, secret_config.type)
            try:
                SecretConstruct(self, secret_config, name_prefix=self._config.project)
            except Exception as exc:
                log.error("Failed to create secret '%s': %s", secret_config.name, exc)
                raise

        log.info("Secrets Manager stack build complete: %d secret(s) defined", total)
