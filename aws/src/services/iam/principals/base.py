from __future__ import annotations

from abc import ABC, abstractmethod

import aws_cdk.aws_iam as iam

from config.models.iam import AssumedByConfig


class BasePrincipal(ABC):
    """
    Strategy interface for IAM principal builders.

    Each concrete strategy knows how to convert an ``AssumedByConfig`` into the
    appropriate CDK ``IPrincipal`` object. The ``IamRoleConstruct`` uses the
    principal registry to select and delegate to the correct strategy.

    Implementors must be stateless — a single instance handles all configs
    of the same principal type via the registry.
    """

    @abstractmethod
    def build(self, config: AssumedByConfig) -> iam.IPrincipal:
        """
        Build and return a CDK IPrincipal from *config*.

        Args:
            config: validated AssumedByConfig for this principal.

        Returns:
            A CDK IPrincipal ready to pass to ``iam.Role(assumed_by=...)``.
        """
