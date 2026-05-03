from __future__ import annotations

from constructs import Construct

from logger import get_logger

log = get_logger(__name__)


class BaseServiceConstruct(Construct):
    """
    Abstract base for every service-level CDK Construct.

    Note: CDK's ``Construct`` uses an incompatible metaclass with ``abc.ABC``,
    so the abstract contract is enforced via ``NotImplementedError`` in
    ``_create_resource()``.  Subclasses that omit it fail at synth time.

    Each concrete subclass wraps exactly one logical AWS resource (or a
    tightly coupled group) and is responsible for implementing
    ``_create_resource()`` to materialise it.

    The constructor is intentionally minimal — all CDK resource creation
    is deferred to ``_create_resource()`` so the lifecycle is explicit and
    testable in isolation.

    Usage::

        class SsmParameterConstruct(BaseServiceConstruct):
            def _create_resource(self) -> None:
                # create the CDK resource for self._config
    """

    def __init__(self, scope: Construct, construct_id: str, config) -> None:
        super().__init__(scope, construct_id)
        self._config = config
        log.debug("Initializing construct: id=%s class=%s", construct_id, self.__class__.__name__)
        try:
            self._create_resource()
        except Exception as exc:
            log.error(
                "Failed to create resource in construct '%s' (%s): %s",
                construct_id,
                self.__class__.__name__,
                exc,
            )
            raise

    def _create_resource(self) -> None:
        """
        Template method — subclasses must override to create CDK resources.
        Called automatically at the end of ``__init__``.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _create_resource()"
        )
