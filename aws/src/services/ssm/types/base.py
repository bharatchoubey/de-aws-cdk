from __future__ import annotations

from abc import ABC, abstractmethod

from constructs import Construct

from config.models.ssm import SsmParameterConfig


class BaseSsmParameter(ABC):
    """
    Strategy interface for SSM parameter type handlers.

    Each concrete strategy knows how to translate one ``SsmParameterConfig``
    into the appropriate CDK L1/L2 construct.  The ``SsmParameterConstruct``
    acts as the context that selects and delegates to the correct strategy.

    Implementors must be stateless — a single instance is shared across
    all parameters of the same type via the handler registry.
    """

    @abstractmethod
    def create(self, scope: Construct, config: SsmParameterConfig) -> None:
        """
        Materialise the CDK construct for the given *config* under *scope*.

        Args:
            scope:  CDK parent construct (the SsmParameterConstruct itself).
            config: validated parameter config for this specific parameter.
        """
