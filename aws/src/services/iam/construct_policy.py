from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_iam as iam
from constructs import Construct

from config.models.iam import IamPolicyConfig, PolicyStatementConfig
from services.base import BaseServiceConstruct


class IamPolicyConstruct(BaseServiceConstruct):
    """
    CDK Construct for a standalone AWS Managed Policy.

    Creates an ``iam.ManagedPolicy`` that exists independently and can be
    attached to multiple roles, users, or groups.  Supports path, tags,
    and all statement fields including NotAction and NotResource.
    """

    def __init__(self, scope: Construct, config: IamPolicyConfig, name_prefix: str = "") -> None:
        cid = f"{name_prefix}-{config.construct_id}" if name_prefix else config.construct_id
        super().__init__(scope, cid, config)

    def _create_resource(self) -> None:
        config: IamPolicyConfig = self._config

        statements = [self._build_statement(s) for s in config.statements]

        policy = iam.ManagedPolicy(
            self,
            "Resource",
            managed_policy_name=config.name,
            description=config.description or None,
            path=config.path,
            statements=statements,
        )

        for key, value in config.tags.items():
            cdk.Tags.of(policy).add(key, value)

    @staticmethod
    def _build_statement(stmt: PolicyStatementConfig) -> iam.PolicyStatement:
        effect = iam.Effect.ALLOW if stmt.effect == "Allow" else iam.Effect.DENY
        policy_stmt = iam.PolicyStatement(effect=effect)

        if stmt.sid:
            policy_stmt.sid = stmt.sid
        if stmt.actions:
            policy_stmt.add_actions(*stmt.actions)
        if stmt.not_actions:
            policy_stmt.add_not_actions(*stmt.not_actions)
        if stmt.resources:
            policy_stmt.add_resources(*stmt.resources)
        if stmt.not_resources:
            policy_stmt.add_not_resources(*stmt.not_resources)
        for condition_key, condition_value in stmt.conditions.items():
            policy_stmt.add_condition(condition_key, condition_value)

        return policy_stmt
