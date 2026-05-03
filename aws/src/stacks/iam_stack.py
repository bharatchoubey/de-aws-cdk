from __future__ import annotations

import aws_cdk.aws_iam as iam
from constructs import Construct

from config.models.iam import IamConfig
from logger import get_logger
from services.iam.construct_group import IamGroupConstruct
from services.iam.construct_oidc_provider import IamOidcProviderConstruct
from services.iam.construct_policy import IamPolicyConstruct
from services.iam.construct_role import IamRoleConstruct
from services.iam.construct_user import IamUserConstruct
from stacks.base import BaseServiceStack

log = get_logger(__name__)


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
        log.info("Creating %d OIDC provider(s)", len(self._config.oidc_providers))
        for oidc_config in self._config.oidc_providers:
            log.debug("Creating OIDC provider: url=%s", oidc_config.url)
            try:
                IamOidcProviderConstruct(self, oidc_config)
            except Exception as exc:
                log.error("Failed to create OIDC provider '%s': %s", oidc_config.url, exc)
                raise

        # 2. Standalone managed policies — no dependencies
        log.info("Creating %d managed policy(ies)", len(self._config.policies))
        for policy_config in self._config.policies:
            log.debug("Creating managed policy: name=%s", policy_config.name)
            try:
                IamPolicyConstruct(self, policy_config)
            except Exception as exc:
                log.error("Failed to create managed policy '%s': %s", policy_config.name, exc)
                raise

        # 3. Groups — must exist before users reference them
        log.info("Creating %d group(s)", len(self._config.groups))
        group_refs: dict[str, iam.IGroup] = {}
        for group_config in self._config.groups:
            log.debug("Creating IAM group: name=%s", group_config.name)
            try:
                construct = IamGroupConstruct(self, group_config)
                group_refs[group_config.name] = construct.group_resource
            except Exception as exc:
                log.error("Failed to create IAM group '%s': %s", group_config.name, exc)
                raise

        # 4. Users — resolved against group_refs built above
        log.info("Creating %d user(s)", len(self._config.users))
        for user_config in self._config.users:
            log.debug("Creating IAM user: name=%s groups=%s", user_config.name, user_config.groups)
            try:
                IamUserConstruct(self, user_config, group_refs)
            except Exception as exc:
                log.error("Failed to create IAM user '%s': %s", user_config.name, exc)
                raise

        # 5. Roles — independent of users/groups
        log.info("Creating %d role(s)", len(self._config.roles))
        for role_config in self._config.roles:
            log.debug("Creating IAM role: name=%s", role_config.name)
            try:
                IamRoleConstruct(self, role_config)
            except Exception as exc:
                log.error("Failed to create IAM role '%s': %s", role_config.name, exc)
                raise

        log.info(
            "IAM stack build complete: %d OIDC provider(s), %d policy(ies), "
            "%d group(s), %d user(s), %d role(s)",
            len(self._config.oidc_providers),
            len(self._config.policies),
            len(self._config.groups),
            len(self._config.users),
            len(self._config.roles),
        )
