from __future__ import annotations

from constructs import Construct

from config.models.secrets_manager import SecretsManagerConfig
from services.secrets_manager.construct import SecretConstruct
from stacks.base import BaseServiceStack


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
        for secret_config in self._config.secrets:
            SecretConstruct(self, secret_config)
