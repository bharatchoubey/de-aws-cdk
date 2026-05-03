from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import aws_cdk as cdk
import aws_cdk.aws_kms as kms
import aws_cdk.aws_secretsmanager as sm
from constructs import Construct

from config.models.secrets_manager import SecretConfig

_REMOVAL_POLICY_MAP = {
    "DESTROY": cdk.RemovalPolicy.DESTROY,
    "RETAIN": cdk.RemovalPolicy.RETAIN,
    "SNAPSHOT": cdk.RemovalPolicy.SNAPSHOT,
}


class BaseSecretType(ABC):
    """
    Strategy interface for Secrets Manager secret type handlers.

    Each concrete strategy knows how to translate one ``SecretConfig`` into
    the appropriate CDK construct for its storage format (PlainText, KeyValue,
    Generated, Reference).  The ``SecretConstruct`` acts as the context that
    selects and delegates to the correct strategy.

    Implementors must be stateless — a single instance is shared across
    all secrets of the same type via the handler registry.

    Shared helpers (``_resolve_kms_key``, ``_apply_managed_secret_fields``) are
    available to all strategies that create an owned ``sm.Secret``.
    The Reference strategy does not use these as it only imports an external secret.
    """

    @abstractmethod
    def create(self, scope: Construct, config: SecretConfig) -> None:
        """
        Materialise the CDK construct for the given *config* under *scope*.

        Args:
            scope:  CDK parent construct (the SecretConstruct itself).
            config: validated secret config for this specific secret.
        """

    @staticmethod
    def _resolve_kms_key(
        scope: Construct, config: SecretConfig
    ) -> Optional[kms.IKey]:
        """
        Resolve a customer-managed KMS key from the config ARN.

        Returns ``None`` when ``kms_key_arn`` is not set, in which case
        Secrets Manager uses the AWS-managed key (aws/secretsmanager).
        """
        if not config.kms_key_arn:
            return None
        return kms.Key.from_key_arn(scope, "KmsKey", config.kms_key_arn)

    @staticmethod
    def _build_replica_regions(
        config: SecretConfig,
    ) -> Optional[list[sm.ReplicaRegion]]:
        """
        Build the ``replica_regions`` list expected by ``sm.Secret``.

        Returns ``None`` when no replicas are configured.
        """
        if not config.replica_regions:
            return None
        return [sm.ReplicaRegion(region=r) for r in config.replica_regions]

    @staticmethod
    def _apply_managed_secret_fields(secret: sm.Secret, config: SecretConfig) -> None:
        """
        Apply fields that are common to all owned (non-Reference) secrets:
          - removal policy
          - tags
        """
        secret.apply_removal_policy(_REMOVAL_POLICY_MAP[config.removal_policy])
        for key, value in config.tags.items():
            cdk.Tags.of(secret).add(key, value)
