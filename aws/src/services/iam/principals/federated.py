from __future__ import annotations

import aws_cdk.aws_iam as iam

from config.models.iam import AssumedByConfig
from services.iam.principals.base import BasePrincipal


class FederatedPrincipal(BasePrincipal):
    """
    Builds an IAM FederatedPrincipal for OIDC / web identity providers.

    Use when a role should be assumed via OpenID Connect federation —
    for example EKS IRSA, GitHub Actions OIDC, or Cognito Identity Pools.

    The ``conditions`` block in the YAML maps directly to the trust policy
    conditions — typically used to restrict which audience or subject can
    assume the role.

    Example config::

        assumed_by:
          type: federated
          principal: token.actions.githubusercontent.com
          conditions:
            StringEquals:
              token.actions.githubusercontent.com:aud: sts.amazonaws.com
            StringLike:
              token.actions.githubusercontent.com:sub: repo:myorg/myrepo:*
    """

    def build(self, config: AssumedByConfig) -> iam.IPrincipal:
        return iam.FederatedPrincipal(
            federated=config.principal,
            conditions=config.conditions,
            assume_role_action="sts:AssumeRoleWithWebIdentity",
        )
