from __future__ import annotations

import aws_cdk.aws_lambda as lambda_
from constructs import Construct

from config.models.lambda_ import LambdaConfig
from logger import get_logger
from services.lambda_.construct_function import LambdaFunctionConstruct
from services.lambda_.construct_layer import LambdaLayerConstruct
from stacks.base import BaseServiceStack

log = get_logger(__name__)


class LambdaStack(BaseServiceStack):
    """
    CDK Stack for AWS Lambda — layers and functions.

    Creation order:
      1. **Layers** — created first so their CDK ``ILayerVersion`` objects are
         available in ``layer_refs`` before any function construct is built.
         Both new layers (from S3 code) and imported layers (by ARN) are
         registered under their logical names so functions can reference either
         kind transparently.

      2. **Functions** — each ``LambdaFunctionConstruct`` receives the full
         ``layer_refs`` dict. Layers listed in ``function.layers`` are resolved
         first by logical name, then by ARN for external layers.

    IAM Roles:
      Functions reference existing IAM roles by ARN (``role_arn``).  No new
      IAM resources are created here — roles are expected to be provisioned by
      the IAM stack and referenced by their ARN in the config.  When
      ``role_arn`` is omitted CDK generates a minimal basic execution role
      automatically.

    Stack ID: ``{project}-{env}-lambda-stack``  (e.g. ``myapp-dev-lambda-stack``)
    """

    def __init__(self, scope: Construct, config: LambdaConfig, **kwargs) -> None:
        super().__init__(scope, "lambda", config, **kwargs)

    def _build(self) -> None:
        total_layers = len(self._config.layers)
        total_functions = len(self._config.functions)
        log.info(
            "Building Lambda stack: %d layer(s), %d function(s) to provision",
            total_layers, total_functions,
        )

        # ── Step 1: Layers ────────────────────────────────────────────────────
        layer_refs: dict[str, lambda_.ILayerVersion] = {}

        for layer_config in self._config.layers:
            log.debug(
                "Creating Lambda layer: name=%s existing_arn=%s",
                layer_config.name,
                layer_config.layer_version_arn or "(new)",
            )
            try:
                construct = LambdaLayerConstruct(
                    self, layer_config, name_prefix=self._config.project
                )
                layer_refs[layer_config.name] = construct.layer_resource
            except Exception as exc:
                log.error(
                    "Failed to create layer '%s': %s", layer_config.name, exc
                )
                raise

        if total_layers:
            log.info(
                "Lambda layers ready: %d layer(s) in layer_refs", len(layer_refs)
            )

        # ── Step 2: Functions ─────────────────────────────────────────────────
        for fn_config in self._config.functions:
            log.debug(
                "Creating Lambda function: name=%s runtime=%s memory=%d timeout=%d role_arn=%s",
                fn_config.name,
                fn_config.runtime,
                fn_config.memory,
                fn_config.timeout,
                fn_config.role_arn or "(CDK default)",
            )
            try:
                LambdaFunctionConstruct(
                    self,
                    fn_config,
                    layer_refs=layer_refs,
                    name_prefix=self._config.project,
                )
            except Exception as exc:
                log.error(
                    "Failed to create Lambda function '%s': %s", fn_config.name, exc
                )
                raise

        log.info(
            "Lambda stack build complete: %d layer(s), %d function(s) defined",
            total_layers, total_functions,
        )
