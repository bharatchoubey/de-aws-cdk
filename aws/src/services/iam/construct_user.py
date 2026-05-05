from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_iam as iam
from constructs import Construct

from config.models.iam import IamUserConfig
from services.base import BaseServiceConstruct


class IamUserConstruct(BaseServiceConstruct):
    """
    CDK Construct for an IAM User.

    Login profiles (passwords) and access keys are intentionally excluded —
    credentials must never be stored in config files.

    Users can be assigned to one or more IAM Groups that are defined in the
    same YAML file.  The ``group_refs`` dict maps group names to resolved
    ``iam.IGroup`` objects created by ``IamGroupConstruct``; the stack
    builds this mapping before creating users.

    Managed policies can also be attached directly to the user.
    """

    def __init__(
        self,
        scope: Construct,
        config: IamUserConfig,
        group_refs: dict[str, iam.IGroup] | None = None,
        name_prefix: str = "",
    ) -> None:
        self._group_refs = group_refs or {}
        cid = f"{name_prefix}-{config.construct_id}" if name_prefix else config.construct_id
        super().__init__(scope, cid, config)

    def _create_resource(self) -> None:
        config: IamUserConfig = self._config

        managed_policies = [
            iam.ManagedPolicy.from_managed_policy_arn(self, f"ManagedPolicy{i}", arn)
            for i, arn in enumerate(config.managed_policies)
        ]
        groups = [self._group_refs[name] for name in config.groups if name in self._group_refs]

        user = iam.User(
            self,
            "Resource",
            user_name=config.name,
            path=config.path,
            managed_policies=managed_policies if managed_policies else None,
            groups=groups if groups else None,
        )

        for key, value in config.tags.items():
            cdk.Tags.of(user).add(key, value)
