from __future__ import annotations

import aws_cdk.aws_iam as iam
from constructs import Construct

from config.models.iam import IamConfig
from services.iam.construct_group import IamGroupConstruct
from services.iam.construct_oidc_provider import IamOidcProviderConstruct
from services.iam.construct_policy import IamPolicyConstruct
from services.iam.construct_role import IamRoleConstruct
from services.iam.construct_user import IamUserConstruct
from stacks.base import BaseServiceStack


class IamStack(BaseServiceStack):
    """
    CDK Stack for AWS IAM resources.

    Manages all IAM resource types from a single config file:
      - OIDC Identity Providers (for EKS IRSA, GitHub Actions, etc.)
      - Managed Policies           (standalone, reusable)
      - Groups                     (created before users for reference wiring)
      - Users                      (assigned to groups via name lookup)
      - Roles                      (single or composite principals)

    Creation order matters: OIDC providers, policies, and groups are created
    first so that users and roles can reference them safely.

    Stack ID: ``{env}-iam-stack``  (e.g. ``dev-iam-stack``)
    """

    def __init__(self, scope: Construct, config: IamConfig, **kwargs) -> None:
        super().__init__(scope, "iam", config, **kwargs)

    def _build(self) -> None:
        # 1. OIDC providers — no dependencies
        for oidc_config in self._config.oidc_providers:
            IamOidcProviderConstruct(self, oidc_config)

        # 2. Standalone managed policies — no dependencies
        for policy_config in self._config.policies:
            IamPolicyConstruct(self, policy_config)

        # 3. Groups — must exist before users reference them
        group_refs: dict[str, iam.IGroup] = {}
        for group_config in self._config.groups:
            construct = IamGroupConstruct(self, group_config)
            group_refs[group_config.name] = construct.group_resource

        # 4. Users — resolved against group_refs built above
        for user_config in self._config.users:
            IamUserConstruct(self, user_config, group_refs)

        # 5. Roles — independent of users/groups
        for role_config in self._config.roles:
            IamRoleConstruct(self, role_config)
