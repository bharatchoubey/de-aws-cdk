from __future__ import annotations

import aws_cdk as cdk
from constructs import Construct

from config.models.base import BaseConfig


class BaseServiceStack(cdk.Stack):
    """
    Abstract base for every service-specific CDK Stack.

    Note: CDK's ``Stack`` uses an incompatible metaclass with ``abc.ABC``,
    so the abstract contract is enforced via ``NotImplementedError`` in
    ``_build()``.  Subclasses that omit ``_build()`` will fail at synth time.

    Responsibilities handled here (once, for all services):
      - Bind the CDK Stack to the correct AWS region from config.
      - Enforce a consistent stack-ID naming convention: {env}-{service}-stack.
      - Apply shared tags (environment, managed-by, service).
      - Invoke the template method ``_build()`` so subclasses only
        implement resource creation, not boilerplate.

    Usage::

        class SsmStack(BaseServiceStack):
            def _build(self) -> None:
                # create CDK constructs here
    """

    def __init__(
        self,
        scope: Construct,
        service_name: str,
        config: BaseConfig,
        **kwargs,
    ) -> None:
        construct_id = f"{config.environment}-{service_name}-stack"
        env = cdk.Environment(region=config.region)
        super().__init__(scope, construct_id, env=env, **kwargs)

        self._config = config
        self._service_name = service_name

        cdk.Tags.of(self).add("environment", config.environment)
        cdk.Tags.of(self).add("managed-by", "de-aws-cdk")
        cdk.Tags.of(self).add("service", service_name)

        self._build()

    def _build(self) -> None:
        """
        Template method — subclasses must override to create CDK resources.
        Called automatically at the end of ``__init__``.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _build()"
        )
