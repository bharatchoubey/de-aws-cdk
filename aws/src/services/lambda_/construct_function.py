from __future__ import annotations

from typing import Optional

import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_lambda_destinations as destinations
import aws_cdk.aws_logs as logs
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_sns as sns
import aws_cdk.aws_sqs as sqs
from constructs import Construct

from config.models.lambda_ import (
    FunctionUrlConfig,
    LambdaAliasConfig,
    LambdaDestinationConfig,
    LambdaDlqConfig,
    LambdaFunctionConfig,
    LambdaVpcConfig,
)
from logger import get_logger
from services.base import BaseServiceConstruct

log = get_logger(__name__)

# ── Mapping tables ─────────────────────────────────────────────────────────────

_RUNTIME_MAP: dict[str, lambda_.Runtime] = {
    "PYTHON_3_8":       lambda_.Runtime.PYTHON_3_8,
    "PYTHON_3_9":       lambda_.Runtime.PYTHON_3_9,
    "PYTHON_3_10":      lambda_.Runtime.PYTHON_3_10,
    "PYTHON_3_11":      lambda_.Runtime.PYTHON_3_11,
    "PYTHON_3_12":      lambda_.Runtime.PYTHON_3_12,
    "NODEJS_18_X":      lambda_.Runtime.NODEJS_18_X,
    "NODEJS_20_X":      lambda_.Runtime.NODEJS_20_X,
    "JAVA_8":           lambda_.Runtime.JAVA_8,
    "JAVA_11":          lambda_.Runtime.JAVA_11,
    "JAVA_17":          lambda_.Runtime.JAVA_17,
    "JAVA_21":          lambda_.Runtime.JAVA_21,
    "DOTNET_6":         lambda_.Runtime.DOTNET_6,
    "RUBY_3_2":         lambda_.Runtime.RUBY_3_2,
    "PROVIDED_AL2":     lambda_.Runtime.PROVIDED_AL2,
    "PROVIDED_AL2023":  lambda_.Runtime.PROVIDED_AL2023,
    "CONTAINER":        lambda_.Runtime.FROM_IMAGE,
}

_ARCHITECTURE_MAP: dict[str, lambda_.Architecture] = {
    "X86_64": lambda_.Architecture.X86_64,
    "ARM_64":  lambda_.Architecture.ARM_64,
}

_TRACING_MAP: dict[str, lambda_.Tracing] = {
    "ACTIVE":       lambda_.Tracing.ACTIVE,
    "PASS_THROUGH": lambda_.Tracing.PASS_THROUGH,
    "DISABLED":     lambda_.Tracing.DISABLED,
}

_LOGGING_FORMAT_MAP: dict[str, lambda_.LoggingFormat] = {
    "TEXT": lambda_.LoggingFormat.TEXT,
    "JSON": lambda_.LoggingFormat.JSON,
}

_LOG_RETENTION_MAP: dict[object, logs.RetentionDays] = {
    1:         logs.RetentionDays.ONE_DAY,
    3:         logs.RetentionDays.THREE_DAYS,
    5:         logs.RetentionDays.FIVE_DAYS,
    7:         logs.RetentionDays.ONE_WEEK,
    14:        logs.RetentionDays.TWO_WEEKS,
    30:        logs.RetentionDays.ONE_MONTH,
    60:        logs.RetentionDays.TWO_MONTHS,
    90:        logs.RetentionDays.THREE_MONTHS,
    120:       logs.RetentionDays.FOUR_MONTHS,
    150:       logs.RetentionDays.FIVE_MONTHS,
    180:       logs.RetentionDays.SIX_MONTHS,
    365:       logs.RetentionDays.ONE_YEAR,
    400:       logs.RetentionDays.THIRTEEN_MONTHS,
    545:       logs.RetentionDays.EIGHTEEN_MONTHS,
    731:       logs.RetentionDays.TWO_YEARS,
    1096:      logs.RetentionDays.THREE_YEARS,
    1827:      logs.RetentionDays.FIVE_YEARS,
    2192:      logs.RetentionDays.SIX_YEARS,
    2557:      logs.RetentionDays.SEVEN_YEARS,
    2922:      logs.RetentionDays.EIGHT_YEARS,
    3288:      logs.RetentionDays.NINE_YEARS,
    3653:      logs.RetentionDays.TEN_YEARS,
    "INFINITE": logs.RetentionDays.INFINITE,
}

_URL_AUTH_MAP: dict[str, lambda_.FunctionUrlAuthType] = {
    "NONE":    lambda_.FunctionUrlAuthType.NONE,
    "AWS_IAM": lambda_.FunctionUrlAuthType.AWS_IAM,
}


class LambdaFunctionConstruct(BaseServiceConstruct):
    """
    CDK Construct for a single Lambda Function covering all L2 features.

    Features implemented:
      - Runtime:            Python, Node.js, Java, .NET, Ruby, Go (provided), Container
      - Code sources:       S3 deployment package, inline string, ECR container image
      - IAM Role:           Imports an existing role by ARN (no new roles created);
                            falls back to a CDK auto-generated basic execution role.
      - Environment vars:   Key/value pairs injected into the function environment.
      - Lambda Layers:      Resolved by logical name (in-stack) or external ARN.
      - VPC:                Places the function in subnets of an existing VPC.
      - Concurrency:        Reserved (cap or throttle) and provisioned (via alias).
      - Dead Letter Queue:  SQS queue or SNS topic for failed invocations.
      - Async destinations: on_success / on_failure — SQS, SNS, EventBridge, Lambda.
      - X-Ray tracing:      ACTIVE | PASS_THROUGH | DISABLED.
      - Logging:            TEXT or JSON log format + CloudWatch log retention.
      - Ephemeral storage:  Configurable /tmp size (512–10240 MB).
      - SnapStart:          Pre-warmed execution snapshots for Java runtimes.
      - Function URL:       Dedicated HTTPS endpoint with optional CORS.
      - Aliases:            Named pointers to published versions with optional
                            provisioned concurrency for cold-start elimination.

    ``layer_refs`` maps logical layer names to already-created ``ILayerVersion``
    objects built by ``LambdaStack`` — same resolution pattern as S3 bucket refs.

    Exposes ``function_resource`` so the stack can publish it or use it as
    a destination in other constructs.
    """

    def __init__(
        self,
        scope: Construct,
        config: LambdaFunctionConfig,
        layer_refs: dict[str, lambda_.ILayerVersion] | None = None,
        name_prefix: str = "",
    ) -> None:
        self.function_resource: Optional[lambda_.Function] = None
        self._layer_refs = layer_refs or {}
        cid = f"{name_prefix}-{config.construct_id}" if name_prefix else config.construct_id
        super().__init__(scope, cid, config)

    def _create_resource(self) -> None:
        config: LambdaFunctionConfig = self._config

        try:
            fn = self._build_function(config)
            self.function_resource = fn

            for key, value in config.tags.items():
                cdk.Tags.of(fn).add(key, value)

            if config.function_url and config.function_url.enabled:
                self._attach_function_url(fn, config.function_url)

            for alias_cfg in config.aliases:
                self._create_alias(fn, alias_cfg)

            log.debug(
                "Lambda function created: name=%s runtime=%s memory=%d timeout=%d",
                config.name, config.runtime, config.memory, config.timeout,
            )

        except Exception as exc:
            log.error("Failed to create Lambda function '%s': %s", config.name, exc)
            raise

    # ── Function builder ───────────────────────────────────────────────────────

    def _build_function(self, config: LambdaFunctionConfig) -> lambda_.Function:
        """Construct the lambda_.Function from config, wiring all optional features."""

        # Create an explicit log group so we control retention and naming.
        # Using log_group avoids the deprecated log_retention prop on Function.
        log_group = logs.LogGroup(
            self,
            "LogGroup",
            log_group_name=f"/aws/lambda/{config.name}",
            retention=self._resolve_log_retention(config.log_retention),
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        fn_kwargs: dict = dict(
            function_name=config.name,
            description=config.description or None,
            runtime=_RUNTIME_MAP[config.runtime],
            handler=(
                lambda_.Handler.FROM_IMAGE
                if config.runtime == "CONTAINER"
                else config.handler
            ),
            code=self._resolve_code(config),
            memory_size=config.memory,
            timeout=cdk.Duration.seconds(config.timeout),
            architecture=_ARCHITECTURE_MAP[config.architecture],
            tracing=_TRACING_MAP[config.tracing],
            logging_format=_LOGGING_FORMAT_MAP[config.log_format],
            log_group=log_group,
            ephemeral_storage_size=cdk.Size.mebibytes(config.ephemeral_storage_size),
            environment=config.environment or None,
            layers=self._resolve_layers(config) or None,
        )

        # IAM role — import existing; omit to let CDK create a basic execution role
        role = self._resolve_role(config)
        if role:
            fn_kwargs["role"] = role

        # VPC
        vpc_kwargs = self._resolve_vpc(config)
        fn_kwargs.update(vpc_kwargs)

        # Dead-letter queue / topic
        dlq_kwargs = self._resolve_dlq(config)
        fn_kwargs.update(dlq_kwargs)

        # Async destinations
        if config.on_success:
            fn_kwargs["on_success"] = self._resolve_destination(
                config.on_success, "OnSuccess"
            )
        if config.on_failure:
            fn_kwargs["on_failure"] = self._resolve_destination(
                config.on_failure, "OnFailure"
            )

        # Reserved concurrency (-1 = unreserved, skip the kwarg entirely)
        if config.reserved_concurrent_executions >= 0:
            fn_kwargs["reserved_concurrent_executions"] = (
                config.reserved_concurrent_executions
            )

        # SnapStart — Java runtimes only; triggers creation of a version automatically
        if config.snap_start:
            fn_kwargs["snap_start"] = lambda_.SnapStartConf.ON_PUBLISHED_VERSIONS

        return lambda_.Function(self, "Resource", **fn_kwargs)

    # ── Code resolution ────────────────────────────────────────────────────────

    def _resolve_code(self, config: LambdaFunctionConfig) -> lambda_.Code:
        code_cfg = config.code
        if code_cfg.type == "S3":
            bucket = s3.Bucket.from_bucket_name(self, "CodeBucket", code_cfg.s3_bucket)
            return lambda_.Code.from_bucket(
                bucket,
                code_cfg.s3_key,
                code_cfg.s3_object_version or None,
            )
        if code_cfg.type == "INLINE":
            return lambda_.Code.from_inline(code_cfg.inline_code)
        if code_cfg.type == "CONTAINER":
            return self._resolve_container_code(code_cfg)
        raise ValueError(f"Unknown code.type: '{code_cfg.type}'")

    def _resolve_container_code(self, code_cfg) -> lambda_.Code:
        """
        Build ECR image code from the repository ARN and image tag.

        Supports optional overrides for CMD, ENTRYPOINT, and WORKDIR.
        """
        repo = ecr.Repository.from_repository_arn(
            self, "EcrRepository", code_cfg.ecr_repo_arn
        )
        image_kwargs: dict = {"tag_or_digest": code_cfg.image_tag}
        if code_cfg.image_cmd:
            image_kwargs["cmd"] = code_cfg.image_cmd
        if code_cfg.image_entrypoint:
            image_kwargs["entrypoint"] = code_cfg.image_entrypoint
        if code_cfg.image_working_directory:
            image_kwargs["working_directory"] = code_cfg.image_working_directory
        return lambda_.Code.from_ecr_image(repo, **image_kwargs)

    # ── IAM role ───────────────────────────────────────────────────────────────

    def _resolve_role(
        self, config: LambdaFunctionConfig
    ) -> Optional[iam.IRole]:
        if not config.role_arn:
            log.debug(
                "Function '%s': no role_arn provided — CDK will create a basic execution role.",
                config.name,
            )
            return None
        log.debug(
            "Function '%s': importing existing IAM role: %s",
            config.name, config.role_arn,
        )
        return iam.Role.from_role_arn(self, "ExecutionRole", config.role_arn)

    # ── VPC ────────────────────────────────────────────────────────────────────

    def _resolve_vpc(self, config: LambdaFunctionConfig) -> dict:
        if not config.vpc or not config.vpc.vpc_id:
            return {}
        vpc_cfg = config.vpc

        # Use from_vpc_attributes instead of from_lookup so synth works without
        # AWS credentials or a resolved account.  The availability zones list is
        # required by CDK but is never used for routing when explicit subnets are
        # provided — we derive placeholder AZs from the stack region.
        stack_region = cdk.Stack.of(self).region
        vpc = ec2.Vpc.from_vpc_attributes(
            self,
            "Vpc",
            vpc_id=vpc_cfg.vpc_id,
            availability_zones=[
                f"{stack_region}a",
                f"{stack_region}b",
                f"{stack_region}c",
            ],
        )
        subnets = [
            ec2.Subnet.from_subnet_id(self, f"Subnet{i}", sid)
            for i, sid in enumerate(vpc_cfg.subnet_ids)
        ]
        security_groups = [
            ec2.SecurityGroup.from_security_group_id(
                self, f"SecurityGroup{i}", sgid,
                allow_all_outbound=True,
            )
            for i, sgid in enumerate(vpc_cfg.security_group_ids)
        ]
        log.debug(
            "Function '%s': attaching to VPC %s (%d subnets, %d security groups)",
            config.name, vpc_cfg.vpc_id,
            len(subnets), len(security_groups),
        )
        return {
            "vpc": vpc,
            "vpc_subnets": ec2.SubnetSelection(subnets=subnets),
            "security_groups": security_groups,
        }

    # ── Dead-letter ────────────────────────────────────────────────────────────

    def _resolve_dlq(self, config: LambdaFunctionConfig) -> dict:
        if not config.dead_letter_queue:
            return {}
        dlq_cfg = config.dead_letter_queue
        if dlq_cfg.type == "SQS":
            queue = sqs.Queue.from_queue_arn(self, "DlqQueue", dlq_cfg.arn)
            return {"dead_letter_queue": queue}
        if dlq_cfg.type == "SNS":
            topic = sns.Topic.from_topic_arn(self, "DlqTopic", dlq_cfg.arn)
            return {"dead_letter_topic": topic}
        return {}

    # ── Async destinations ─────────────────────────────────────────────────────

    def _resolve_destination(
        self,
        dest_cfg: LambdaDestinationConfig,
        id_suffix: str,
    ) -> lambda_.IDestination:
        if dest_cfg.type == "SQS":
            queue = sqs.Queue.from_queue_arn(
                self, f"{id_suffix}Queue", dest_cfg.arn
            )
            return destinations.SqsDestination(queue)
        if dest_cfg.type == "SNS":
            topic = sns.Topic.from_topic_arn(
                self, f"{id_suffix}Topic", dest_cfg.arn
            )
            return destinations.SnsDestination(topic)
        if dest_cfg.type == "EVENTBRIDGE":
            # Empty EventBridgeDestination sends to the default event bus.
            # If an ARN is provided, we can use it directly via the ARN string —
            # CDK EventBridgeDestination currently doesn't accept an IEventBus from ARN,
            # so we use the default bus (which is the most common EventBridge use case).
            return destinations.EventBridgeDestination()
        if dest_cfg.type == "LAMBDA":
            fn = lambda_.Function.from_function_arn(
                self, f"{id_suffix}Fn", dest_cfg.arn
            )
            return destinations.LambdaDestination(fn)
        raise ValueError(f"Unknown destination type: '{dest_cfg.type}'")

    # ── Layers ─────────────────────────────────────────────────────────────────

    def _resolve_layers(
        self, config: LambdaFunctionConfig
    ) -> list[lambda_.ILayerVersion]:
        result: list[lambda_.ILayerVersion] = []
        for ref in config.layers:
            if ref.startswith("arn:"):
                # External layer ARN — import by ARN directly
                short_id = ref.split(":")[-2]  # layer name segment
                layer = lambda_.LayerVersion.from_layer_version_arn(
                    self, f"ExtLayer-{short_id}", ref
                )
                result.append(layer)
            elif ref in self._layer_refs:
                # In-stack logical name resolved from layer_refs
                result.append(self._layer_refs[ref])
            else:
                log.warning(
                    "Function '%s': layer reference '%s' was not found in stack "
                    "layer_refs and does not look like an ARN — skipping.",
                    config.name, ref,
                )
        return result

    # ── Log retention ──────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_log_retention(retention: object) -> logs.RetentionDays:
        key = "INFINITE" if str(retention) == "INFINITE" else int(retention)
        if key not in _LOG_RETENTION_MAP:
            log.warning(
                "log_retention %s is not in the supported set; defaulting to ONE_MONTH.",
                retention,
            )
            return logs.RetentionDays.ONE_MONTH
        return _LOG_RETENTION_MAP[key]

    # ── Function URL ───────────────────────────────────────────────────────────

    def _attach_function_url(
        self, fn: lambda_.Function, url_cfg: FunctionUrlConfig
    ) -> None:
        cors: Optional[lambda_.FunctionUrlCorsOptions] = None
        if url_cfg.cors:
            c = url_cfg.cors
            cors = lambda_.FunctionUrlCorsOptions(
                allowed_origins=c.allow_origins,
                allowed_methods=[lambda_.HttpMethod.ALL]
                if "*" in c.allow_methods
                else [lambda_.HttpMethod(m.upper()) for m in c.allow_methods],
                allowed_headers=c.allow_headers or None,
                exposed_headers=c.expose_headers or None,
                max_age=cdk.Duration.seconds(c.max_age) if c.max_age else None,
            )
        fn.add_function_url(auth_type=_URL_AUTH_MAP[url_cfg.auth_type], cors=cors)
        log.debug(
            "Function URL attached: auth_type=%s cors=%s",
            url_cfg.auth_type, bool(cors),
        )

    # ── Alias ──────────────────────────────────────────────────────────────────

    def _create_alias(
        self, fn: lambda_.Function, alias_cfg: LambdaAliasConfig
    ) -> None:
        alias_kwargs: dict = {
            "alias_name": alias_cfg.name,
            "version": fn.current_version,
        }
        if alias_cfg.description:
            alias_kwargs["description"] = alias_cfg.description
        if alias_cfg.provisioned_concurrent_executions > 0:
            alias_kwargs["provisioned_concurrent_executions"] = (
                alias_cfg.provisioned_concurrent_executions
            )
        lambda_.Alias(self, f"Alias-{alias_cfg.name}", **alias_kwargs)
        log.debug(
            "Lambda alias created: function=%s alias=%s provisioned=%d",
            fn.function_name,
            alias_cfg.name,
            alias_cfg.provisioned_concurrent_executions,
        )
