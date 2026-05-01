from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_secretsmanager as sm
from constructs import Construct

from config.models.secrets_manager import SecretConfig
from services.secrets_manager.env_resolver import resolve
from services.secrets_manager.types.base import BaseSecretType


class KeyValueSecret(BaseSecretType):
    """
    Creates an AWS Secrets Manager secret containing a JSON key-value object.

    Each value in the YAML dict supports ``${VAR}`` tokens which are resolved
    from environment variables at CDK synth time.  If any referenced variable
    is not set, an ``EnvironmentError`` is raised immediately so the problem
    surfaces before deployment rather than at runtime.

    Each key in the stored JSON is individually retrievable at runtime via the
    AWS SDK using ``jsonField``.

    Suitable for: grouped credentials (username + password + host + port)
    consumed together by a single service.
    """

    def create(self, scope: Construct, config: SecretConfig) -> None:
        resolved_dict: dict = resolve(config.value)
        sm.Secret(
            scope,
            "Resource",
            secret_name=config.name,
            description=config.description or None,
            secret_object_value={
                key: cdk.SecretValue.unsafe_plain_text(str(val))
                for key, val in resolved_dict.items()
            },
        )
