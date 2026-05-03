from __future__ import annotations

import aws_cdk.aws_iam as iam

from config.models.iam import AssumedByConfig
from services.iam.principals.base import BasePrincipal


class AccountPrincipal(BasePrincipal):
    """
    Builds an IAM AccountPrincipal for cross-account role assumption.

    Use when the role should be assumable by all identities within a
    specific AWS account (e.g. for cross-account access patterns).

    Example config::

        assumed_by:
          type: account
          principal: "123456789012"
    """

    def build(self, config: AssumedByConfig) -> iam.IPrincipal:
        return iam.AccountPrincipal(config.principal)
