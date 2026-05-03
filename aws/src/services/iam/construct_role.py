from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_iam as iam
from constructs import Construct

from config.models.iam import IamRoleConfig, PolicyStatementConfig
from services.base import BaseServiceConstruct
from services.iam.principals import build_principal


class IamRoleConstruct(BaseServiceConstruct):
    """
    CDK Construct for a single IAM Role.

    Handles all role composition in one place:
      - Resolves trust principal(s) via the principal strategy registry
        (supports single and composite principals).
      - Attaches AWS-managed and customer-managed policies by ARN.
      - Embeds inline policy documents built from config statements.
      - Applies permission boundary if specified.
      - Sets path and max session duration.
      - Applies resource tags.
    """

    def __init__(self, scope: Construct, config: IamRoleConfig, name_prefix: str = "") -> None:
        cid = f"{name_prefix}-{config.construct_id}" if name_prefix else config.construct_id
        super().__init__(scope, cid, config)

    def _create_resource(self) -> None:
        config: IamRoleConfig = self._config

        principal = build_principal(config.assumed_by)
        managed_policies = self._build_managed_policies(config)
        inline_policies = self._build_inline_policies(config)
        permission_boundary = self._build_permission_boundary(config)

        role = iam.Role(
            self,
            "Resource",
            role_name=config.name,
            description=config.description or None,
            path=config.path,
            assumed_by=principal,
            managed_policies=managed_policies if managed_policies else None,
            inline_policies=inline_policies if inline_policies else None,
            permissions_boundary=permission_boundary,
            max_session_duration=cdk.Duration.hours(config.max_session_duration_hours),
        )

        for key, value in config.tags.items():
            cdk.Tags.of(role).add(key, value)

    def _build_managed_policies(self, config: IamRoleConfig) -> list:
        return [
            iam.ManagedPolicy.from_managed_policy_arn(self, f"ManagedPolicy{i}", arn)
            for i, arn in enumerate(config.managed_policies)
        ]

    def _build_inline_policies(self, config: IamRoleConfig) -> dict:
        result = {}
        for inline in config.inline_policies:
            result[inline.name] = iam.PolicyDocument(
                statements=[self._build_statement(s) for s in inline.statements]
            )
        return result

    def _build_permission_boundary(self, config: IamRoleConfig):
        if not config.permission_boundary:
            return None
        return iam.ManagedPolicy.from_managed_policy_arn(
            self, "PermissionBoundary", config.permission_boundary
        )

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
