from __future__ import annotations

from typing import Union

import aws_cdk.aws_iam as iam

from config.models.iam import AssumedByConfig
from logger import get_logger
from services.iam.principals.account import AccountPrincipal
from services.iam.principals.arn import ArnPrincipal
from services.iam.principals.base import BasePrincipal
from services.iam.principals.federated import FederatedPrincipal
from services.iam.principals.saml import SamlPrincipal
from services.iam.principals.service import ServicePrincipal

log = get_logger(__name__)

_PRINCIPAL_BUILDERS: dict[str, BasePrincipal] = {
    "service": ServicePrincipal(),
    "account": AccountPrincipal(),
    "arn": ArnPrincipal(),
    "federated": FederatedPrincipal(),
    "saml": SamlPrincipal(),
}


def build_principal(configs: list[AssumedByConfig]) -> iam.IPrincipal:
    """
    Build a CDK IPrincipal from one or more AssumedByConfig entries.

    - Single entry  → delegates directly to the matching strategy.
    - Multiple entries → wraps all resolved principals in a CompositePrincipal
      so that multiple services/accounts/identities can assume the same role.

    Raises:
        ValueError: if any config.type is not in the registry.
    """
    if not configs:
        raise ValueError("at least one 'assumed_by' entry is required.")

    resolved = []
    try:
        for config in configs:
            builder = _PRINCIPAL_BUILDERS.get(config.type)
            if builder is None:
                supported = ", ".join(sorted(_PRINCIPAL_BUILDERS))
                raise ValueError(
                    f"Unsupported principal type: '{config.type}'. "
                    f"Supported types: [{supported}]"
                )
            log.debug("Building principal: type=%s principal=%s", config.type, config.principal)
            resolved.append(builder.build(config))
    except ValueError:
        log.error("Invalid principal configuration: %s", [c.type for c in configs])
        raise
    except Exception as exc:
        log.error("Unexpected error building principals: %s", exc)
        raise

    if len(resolved) == 1:
        return resolved[0]

    log.debug("Composing %d principals into CompositePrincipal", len(resolved))
    return iam.CompositePrincipal(*resolved)


__all__ = [
    "BasePrincipal",
    "ServicePrincipal",
    "AccountPrincipal",
    "ArnPrincipal",
    "FederatedPrincipal",
    "SamlPrincipal",
    "build_principal",
]
