from __future__ import annotations

import aws_cdk.aws_iam as iam

from config.models.iam import AssumedByConfig
from services.iam.principals.base import BasePrincipal


class ServicePrincipal(BasePrincipal):
    """
    Builds an IAM ServicePrincipal for AWS service identities.

    Use when the role should be assumable by an AWS service such as
    EC2, Lambda, ECS tasks, API Gateway, etc.

    Example config::

        assumed_by:
          type: service
          principal: lambda.amazonaws.com
    """

    def build(self, config: AssumedByConfig) -> iam.IPrincipal:
        return iam.ServicePrincipal(config.principal)
