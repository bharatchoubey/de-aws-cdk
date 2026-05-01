from __future__ import annotations

from abc import ABC, abstractmethod

from constructs import Construct

from config.models.secrets_manager import SecretConfig


class BaseSecretType(ABC):
    """
    Strategy interface for Secrets Manager secret type handlers.

    Each concrete strategy knows how to translate one ``SecretConfig`` into
    the appropriate CDK construct for its storage format (PlainText, KeyValue).
    The ``SecretConstruct`` acts as the context that selects and delegates to
    the correct strategy.

    Implementors must be stateless — a single instance is shared across
    all secrets of the same type via the handler registry.
    """

    @abstractmethod
    def create(self, scope: Construct, config: SecretConfig) -> None:
        """
        Materialise the CDK construct for the given *config* under *scope*.

        Args:
            scope:  CDK parent construct (the SecretConstruct itself).
            config: validated secret config for this specific secret.
        """
