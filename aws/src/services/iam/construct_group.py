from __future__ import annotations

import aws_cdk.aws_iam as iam
from constructs import Construct

from config.models.iam import IamGroupConfig
from services.base import BaseServiceConstruct


class IamGroupConstruct(BaseServiceConstruct):
    """
    CDK Construct for an IAM Group.

    Groups provide a logical way to attach permissions to multiple users at
    once.  Users in the same YAML file reference groups by name under
    ``IamUserConfig.groups``; the stack creates groups first and passes
    ``IGroup`` references to user constructs.

    The resolved ``iam.Group`` object is stored on ``self.group_resource``
    so that ``IamStack`` can collect group references for user wiring.
    """

    def __init__(self, scope: Construct, config: IamGroupConfig) -> None:
        self.group_resource: iam.Group = None
        super().__init__(scope, config.construct_id, config)

    def _create_resource(self) -> None:
        config: IamGroupConfig = self._config

        managed_policies = [
            iam.ManagedPolicy.from_managed_policy_arn(self, f"ManagedPolicy{i}", arn)
            for i, arn in enumerate(config.managed_policies)
        ]

        self.group_resource = iam.Group(
            self,
            "Resource",
            group_name=config.name,
            path=config.path,
            managed_policies=managed_policies if managed_policies else None,
        )
