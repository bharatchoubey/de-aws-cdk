from __future__ import annotations

import aws_cdk.aws_secretsmanager as sm
from constructs import Construct

from config.models.secrets_manager import SecretConfig
from services.secrets_manager.types.base import BaseSecretType


class ReferenceSecret(BaseSecretType):
    """
    Registers a reference to an AWS Secrets Manager secret that already exists.

    CDK creates an ``ISecret`` reference object only — it does not read, write,
    or manage the secret value in any way. The secret must have been created
    previously (manually via the AWS console/CLI, by Terraform, or by another
    process).

    Use cases:
      - Secrets owned by another team or tool that CDK stacks need to reference
        for IAM policy bindings or cross-stack wiring.
      - Importing legacy secrets into the CDK dependency graph without
        taking over their lifecycle.
    """

    def create(self, scope: Construct, config: SecretConfig) -> None:
        sm.Secret.from_secret_name_v2(
            scope,
            "Resource",
            secret_name=config.name,
        )
