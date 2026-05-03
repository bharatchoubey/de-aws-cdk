from __future__ import annotations

import aws_cdk.aws_iam as iam

from config.models.iam import AssumedByConfig
from services.iam.principals.base import BasePrincipal


class ArnPrincipal(BasePrincipal):
    """
    Builds an IAM ArnPrincipal for a specific IAM identity ARN.

    Use when the role should be assumable by a specific user, role, or
    federated identity identified by its full ARN.

    Example config::

        assumed_by:
          type: arn
          principal: arn:aws:iam::123456789012:role/DeploymentRole
    """

    def build(self, config: AssumedByConfig) -> iam.IPrincipal:
        return iam.ArnPrincipal(config.principal)
