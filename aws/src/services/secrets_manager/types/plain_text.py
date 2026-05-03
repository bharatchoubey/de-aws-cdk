from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_secretsmanager as sm
from constructs import Construct

from config.models.secrets_manager import SecretConfig
from services.secrets_manager.env_resolver import resolve
from services.secrets_manager.types.base import BaseSecretType


class PlainTextSecret(BaseSecretType):
    """
    Creates an AWS Secrets Manager secret containing a single string value.

    The ``value`` field supports ``${VAR}`` tokens which are resolved from
    environment variables at CDK synth time.  If any referenced variable is
    not set, an ``EnvironmentError`` is raised immediately so the problem
    surfaces before deployment rather than at runtime.

    Supports tags, removal policy, KMS encryption, and cross-region replication.

    Suitable for: API tokens, signing keys, single-value credentials.
    """

    def create(self, scope: Construct, config: SecretConfig) -> None:
        resolved_value = resolve(config.value)
        encryption_key = self._resolve_kms_key(scope, config)
        replica_regions = self._build_replica_regions(config)

        secret = sm.Secret(
            scope,
            "Resource",
            secret_name=config.name,
            description=config.description or None,
            secret_string_value=cdk.SecretValue.unsafe_plain_text(resolved_value),
            encryption_key=encryption_key,
            replica_regions=replica_regions,
        )
        self._apply_managed_secret_fields(secret, config)
