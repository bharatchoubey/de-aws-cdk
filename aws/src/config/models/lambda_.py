from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from config.models.base import BaseConfig

# ── Validation sets ────────────────────────────────────────────────────────────

VALID_RUNTIMES = {
    "PYTHON_3_8", "PYTHON_3_9", "PYTHON_3_10", "PYTHON_3_11", "PYTHON_3_12",
    "NODEJS_18_X", "NODEJS_20_X", "NODEJS_22_X",
    "JAVA_8", "JAVA_11", "JAVA_17", "JAVA_21",
    "DOTNET_6", "DOTNET_8",
    "RUBY_3_2", "RUBY_3_3",
    "PROVIDED_AL2", "PROVIDED_AL2023",
    "CONTAINER",
}

VALID_ARCHITECTURES = {"X86_64", "ARM_64"}
VALID_CODE_TYPES = {"S3", "INLINE", "CONTAINER"}
VALID_TRACING = {"ACTIVE", "PASS_THROUGH", "DISABLED"}
VALID_DLQ_TYPES = {"SQS", "SNS"}
VALID_DESTINATION_TYPES = {"SQS", "SNS", "EVENTBRIDGE", "LAMBDA"}
VALID_AUTH_TYPES = {"NONE", "AWS_IAM"}
VALID_LOG_FORMATS = {"TEXT", "JSON"}

# All CloudWatch Logs retention periods supported by Lambda's log_retention prop
_VALID_RETENTION_DAYS = {
    1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365,
    400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653,
}


# ── Code ───────────────────────────────────────────────────────────────────────

@dataclass
class LambdaCodeConfig:
    """
    Code source for a Lambda function or layer.

    S3:        Deployment package (zip) stored in S3.
    INLINE:    Inline code string (≤ 4 KB; dev/testing only — not for layers).
    CONTAINER: Pre-built ECR container image.

    Fields:
        type:                S3 | INLINE | CONTAINER
        s3_bucket:           Bucket name (S3 only)
        s3_key:              Object key, e.g. functions/api.zip (S3 only)
        s3_object_version:   Specific S3 object version (S3 only, optional)
        inline_code:         Raw source code string (INLINE only)
        ecr_repo_arn:        Full ECR repository ARN (CONTAINER only)
        image_tag:           Image tag or digest (CONTAINER only, default "latest")
        image_cmd:           Override container CMD
        image_entrypoint:    Override container ENTRYPOINT
        image_working_directory: Override container WORKDIR
    """

    type: str = "S3"
    # S3 fields
    s3_bucket: str = ""
    s3_key: str = ""
    s3_object_version: str = ""
    # INLINE fields
    inline_code: str = ""
    # CONTAINER fields
    ecr_repo_arn: str = ""
    image_tag: str = "latest"
    image_cmd: list[str] = field(default_factory=list)
    image_entrypoint: list[str] = field(default_factory=list)
    image_working_directory: str = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.type not in VALID_CODE_TYPES:
            raise ValueError(
                f"code.type must be one of {VALID_CODE_TYPES}. Got: '{self.type}'"
            )
        if self.type == "S3":
            if not self.s3_bucket or not self.s3_key:
                raise ValueError("code.type=S3 requires both 's3_bucket' and 's3_key'.")
        elif self.type == "INLINE":
            if not self.inline_code:
                raise ValueError("code.type=INLINE requires 'inline_code'.")
        elif self.type == "CONTAINER":
            if not self.ecr_repo_arn:
                raise ValueError(
                    "code.type=CONTAINER requires 'ecr_repo_arn' "
                    "(full ECR repository ARN)."
                )


# ── VPC ────────────────────────────────────────────────────────────────────────

@dataclass
class LambdaVpcConfig:
    """
    Places the Lambda function inside an existing VPC.

    Fields:
        vpc_id:              Existing VPC ID (e.g. vpc-0abc123)
        subnet_ids:          Subnets the function is attached to (at least one)
        security_group_ids:  Security groups controlling network access
    """

    vpc_id: str = ""
    subnet_ids: list[str] = field(default_factory=list)
    security_group_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.vpc_id and not self.subnet_ids:
            raise ValueError("vpc config requires at least one 'subnet_id'.")


# ── Dead-Letter Queue ──────────────────────────────────────────────────────────

@dataclass
class LambdaDlqConfig:
    """
    Dead-letter destination for failed asynchronous invocations.

    Fields:
        type:  SQS (maps to dead_letter_queue) | SNS (maps to dead_letter_topic)
        arn:   Full ARN of the SQS queue or SNS topic
    """

    type: str = "SQS"
    arn: str = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.type not in VALID_DLQ_TYPES:
            raise ValueError(
                f"dead_letter_queue.type must be one of {VALID_DLQ_TYPES}. "
                f"Got: '{self.type}'"
            )
        if not self.arn:
            raise ValueError("dead_letter_queue.arn must be provided.")


# ── Async Destination ──────────────────────────────────────────────────────────

@dataclass
class LambdaDestinationConfig:
    """
    Async invocation destination for on_success / on_failure.

    Fields:
        type:  SQS | SNS | EVENTBRIDGE | LAMBDA
        arn:   Resource ARN (omit for EVENTBRIDGE default event bus)
    """

    type: str = "SQS"
    arn: str = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.type not in VALID_DESTINATION_TYPES:
            raise ValueError(
                f"destination.type must be one of {VALID_DESTINATION_TYPES}. "
                f"Got: '{self.type}'"
            )
        if self.type != "EVENTBRIDGE" and not self.arn:
            raise ValueError(
                f"destination.arn is required for type '{self.type}'."
            )


# ── Function URL ───────────────────────────────────────────────────────────────

@dataclass
class FunctionUrlCorsConfig:
    """
    CORS settings for a Lambda Function URL.

    Fields:
        allow_origins:  Allowed origins (["*"] for public)
        allow_methods:  HTTP methods (["*"] for all)
        allow_headers:  Request headers to allow
        expose_headers: Response headers accessible to the browser
        max_age:        Seconds the browser may cache preflight responses
    """

    allow_origins: list[str] = field(default_factory=lambda: ["*"])
    allow_methods: list[str] = field(default_factory=lambda: ["*"])
    allow_headers: list[str] = field(default_factory=list)
    expose_headers: list[str] = field(default_factory=list)
    max_age: int = 0


@dataclass
class FunctionUrlConfig:
    """
    Lambda Function URL — exposes the function via a dedicated HTTPS endpoint.

    Fields:
        enabled:    Must be true to create the URL.
        auth_type:  NONE (public) | AWS_IAM (IAM-authenticated)
        cors:       Optional CORS configuration
    """

    enabled: bool = False
    auth_type: str = "NONE"
    cors: Optional[FunctionUrlCorsConfig] = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.auth_type not in VALID_AUTH_TYPES:
            raise ValueError(
                f"function_url.auth_type must be one of {VALID_AUTH_TYPES}. "
                f"Got: '{self.auth_type}'"
            )


# ── Alias ──────────────────────────────────────────────────────────────────────

@dataclass
class LambdaAliasConfig:
    """
    Lambda function alias — stable pointer to a published function version.

    Used for blue/green deployments, traffic splitting, and provisioned
    concurrency (warm instances that eliminate cold starts).

    Fields:
        name:                              Alias name (e.g. 'live', 'stable')
        description:                       Free-text description
        provisioned_concurrent_executions: Number of pre-warmed execution environments (0 = disabled)
    """

    name: str = ""
    description: str = ""
    provisioned_concurrent_executions: int = 0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("alias.name must be a non-empty string.")
        if self.provisioned_concurrent_executions < 0:
            raise ValueError(
                f"alias.provisioned_concurrent_executions must be >= 0. "
                f"Got: {self.provisioned_concurrent_executions}"
            )


# ── Layer ──────────────────────────────────────────────────────────────────────

_PYTHON_RUNTIMES = {r for r in VALID_RUNTIMES if r.startswith("PYTHON_")}
_NODEJS_RUNTIMES = {r for r in VALID_RUNTIMES if r.startswith("NODEJS_")}
# Runtimes that support Docker-based package installation
VALID_BUILD_RUNTIMES = _PYTHON_RUNTIMES | _NODEJS_RUNTIMES


@dataclass
class LambdaLayerConfig:
    """
    Lambda Layer — shared dependency package attached to one or more functions.

    Three creation modes (mutually exclusive):

    1. **packages** (recommended):
       List package names/versions directly in the YAML.  CDK runs ``pip install``
       or ``npm install`` inside a Lambda-compatible Docker container at synth time.
       Requires Docker to be running.  ``build_runtime`` must also be set to tell
       CDK which Docker image to use.

       Python example:  packages: [requests==2.31.0, pydantic==2.5.0]
       Node.js example: packages: [lodash@4.17.21, axios@1.6.0]

    2. **code** (pre-built zip in S3):
       You build and upload the zip yourself; CDK just points CloudFormation at it.
       No Docker required.

    3. **layer_version_arn** (existing layer reference):
       CDK imports the layer by ARN — no new AWS resource is created.

    Fields:
        name:                     Logical name — used for in-stack cross-references.
        description:              Free-text description.
        compatible_runtimes:      Runtimes that can use this layer.
        compatible_architectures: CPU architectures (X86_64 | ARM_64).
        removal_policy:           RETAIN (default) | DESTROY.
        license:                  SPDX license identifier (e.g. 'MIT').
        packages:                 Package list for Docker-based installation.
                                  Python: ["requests==2.31.0", "pydantic==2.5.0"]
                                  Node.js: ["lodash@4.17.21", "axios@1.6.0"]
        build_runtime:            Runtime whose Docker image is used for installation.
                                  Required when 'packages' is set.
                                  Must be a Python or Node.js runtime.
        code:                     S3 pre-built zip config (alternative to packages).
        layer_version_arn:        ARN of an existing layer (skips creation entirely).
    """

    name: str = ""
    description: str = ""
    compatible_runtimes: list[str] = field(default_factory=list)
    compatible_architectures: list[str] = field(default_factory=list)
    removal_policy: str = "RETAIN"
    license: str = ""
    # Mode 1 — Docker-based package installation
    packages: list[str] = field(default_factory=list)
    build_runtime: str = ""
    # Mode 2 — pre-built S3 zip
    code: Optional[LambdaCodeConfig] = None
    # Mode 3 — reference existing layer
    layer_version_arn: str = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("layer.name must be a non-empty string.")

        modes = [
            bool(self.packages),
            bool(self.code),
            bool(self.layer_version_arn),
        ]
        if not any(modes):
            raise ValueError(
                f"layer '{self.name}': provide one of: 'packages' (Docker install), "
                f"'code' (S3 pre-built zip), or 'layer_version_arn' (existing layer)."
            )
        if sum(modes) > 1:
            raise ValueError(
                f"layer '{self.name}': 'packages', 'code', and 'layer_version_arn' "
                f"are mutually exclusive — provide exactly one."
            )

        if self.packages:
            if not self.build_runtime:
                raise ValueError(
                    f"layer '{self.name}': 'build_runtime' is required when "
                    f"'packages' is set. It selects the Docker image used for "
                    f"pip/npm installation."
                )
            if self.build_runtime not in VALID_BUILD_RUNTIMES:
                raise ValueError(
                    f"layer '{self.name}': 'build_runtime' must be a Python or "
                    f"Node.js runtime. Got: '{self.build_runtime}'. "
                    f"Valid: {sorted(VALID_BUILD_RUNTIMES)}"
                )

        if self.removal_policy not in {"DESTROY", "RETAIN"}:
            raise ValueError(
                f"layer '{self.name}' removal_policy must be DESTROY or RETAIN. "
                f"Got: '{self.removal_policy}'"
            )
        for rt in self.compatible_runtimes:
            if rt not in VALID_RUNTIMES:
                raise ValueError(
                    f"layer '{self.name}': compatible_runtime '{rt}' must be one of "
                    f"{VALID_RUNTIMES}."
                )
        for arch in self.compatible_architectures:
            if arch not in VALID_ARCHITECTURES:
                raise ValueError(
                    f"layer '{self.name}': compatible_architecture '{arch}' must be one of "
                    f"{VALID_ARCHITECTURES}."
                )

    @property
    def construct_id(self) -> str:
        """Safe CDK construct ID derived from the logical layer name."""
        return self.name.replace("/", "-").replace("_", "-")


# ── Function ───────────────────────────────────────────────────────────────────

@dataclass
class LambdaFunctionConfig:
    """
    Configuration for a single Lambda function covering all CDK L2 features.

    Compute:
        name:                          Function name (also used as logical ID).
        description:                   Free-text description.
        runtime:                       Execution runtime (see VALID_RUNTIMES).
        handler:                       Module.function entrypoint (e.g. app.handler).
        architecture:                  X86_64 (default) | ARM_64.
        memory:                        Memory allocation in MB (128–10240).
        timeout:                       Max execution time in seconds (1–900).
        ephemeral_storage_size:        /tmp storage in MB (512–10240, default 512).

    Code:
        code:                          Source code configuration.

    IAM:
        role_arn:                      ARN of an existing IAM execution role.
                                       Omit to let CDK create a basic execution role.
                                       Use the role created by the IAM stack.

    Configuration:
        environment:                   Environment variables (key → value).
        layers:                        List of logical layer names (in-stack) or
                                       external layer ARNs.

    Networking:
        vpc:                           Place the function inside an existing VPC.

    Concurrency:
        reserved_concurrent_executions: -1 = unreserved; 0 = throttled; > 0 = capped.

    Reliability:
        dead_letter_queue:             SQS queue or SNS topic for failed invocations.
        on_success:                    Async destination for successful invocations.
        on_failure:                    Async destination for failed invocations.

    Observability:
        tracing:                       X-Ray tracing (ACTIVE | PASS_THROUGH | DISABLED).
        log_format:                    TEXT (default) | JSON structured logging.
        log_retention:                 CloudWatch log retention in days (or INFINITE).

    Performance:
        snap_start:                    SnapStart for Java runtimes (eliminates cold starts).

    Exposure:
        function_url:                  Dedicated HTTPS endpoint (auth_type NONE | AWS_IAM).

    Deployment:
        aliases:                       Stable version pointers (with optional provisioned concurrency).

    tags:                              Resource tags applied to the function.
    """

    name: str = ""
    description: str = ""
    handler: str = "app.handler"
    runtime: str = "PYTHON_3_11"
    memory: int = 128
    timeout: int = 30
    architecture: str = "X86_64"
    ephemeral_storage_size: int = 512

    code: Optional[LambdaCodeConfig] = None
    role_arn: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    layers: list[str] = field(default_factory=list)

    vpc: Optional[LambdaVpcConfig] = None
    reserved_concurrent_executions: int = -1

    dead_letter_queue: Optional[LambdaDlqConfig] = None
    on_success: Optional[LambdaDestinationConfig] = None
    on_failure: Optional[LambdaDestinationConfig] = None

    tracing: str = "DISABLED"
    log_format: str = "TEXT"
    log_retention: object = 30          # int (days) or "INFINITE"

    snap_start: bool = False

    function_url: Optional[FunctionUrlConfig] = None
    aliases: list[LambdaAliasConfig] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("function.name must be a non-empty string.")
        if self.runtime not in VALID_RUNTIMES:
            raise ValueError(
                f"function '{self.name}': runtime must be one of "
                f"{VALID_RUNTIMES}. Got: '{self.runtime}'"
            )
        if self.architecture not in VALID_ARCHITECTURES:
            raise ValueError(
                f"function '{self.name}': architecture must be one of "
                f"{VALID_ARCHITECTURES}. Got: '{self.architecture}'"
            )
        if not self.code:
            raise ValueError(
                f"function '{self.name}': 'code' block is required."
            )
        if self.runtime == "CONTAINER" and self.code.type != "CONTAINER":
            raise ValueError(
                f"function '{self.name}': CONTAINER runtime requires code.type=CONTAINER."
            )
        if self.runtime != "CONTAINER" and self.code.type == "CONTAINER":
            raise ValueError(
                f"function '{self.name}': code.type=CONTAINER requires runtime=CONTAINER."
            )
        if not 128 <= self.memory <= 10240:
            raise ValueError(
                f"function '{self.name}': memory must be 128–10240 MB. Got: {self.memory}"
            )
        if not 1 <= self.timeout <= 900:
            raise ValueError(
                f"function '{self.name}': timeout must be 1–900 seconds. Got: {self.timeout}"
            )
        if not 512 <= self.ephemeral_storage_size <= 10240:
            raise ValueError(
                f"function '{self.name}': ephemeral_storage_size must be 512–10240 MB. "
                f"Got: {self.ephemeral_storage_size}"
            )
        if self.tracing not in VALID_TRACING:
            raise ValueError(
                f"function '{self.name}': tracing must be one of {VALID_TRACING}. "
                f"Got: '{self.tracing}'"
            )
        if self.log_format not in VALID_LOG_FORMATS:
            raise ValueError(
                f"function '{self.name}': log_format must be one of {VALID_LOG_FORMATS}. "
                f"Got: '{self.log_format}'"
            )
        retention = self.log_retention
        if str(retention) != "INFINITE":
            try:
                if int(retention) not in _VALID_RETENTION_DAYS:
                    raise ValueError(
                        f"function '{self.name}': log_retention {retention} is not a valid "
                        f"CloudWatch retention period. Valid values: {sorted(_VALID_RETENTION_DAYS)} "
                        f"or 'INFINITE'."
                    )
            except (TypeError, ValueError) as exc:
                if "not a valid" not in str(exc):
                    raise ValueError(
                        f"function '{self.name}': log_retention must be an integer or 'INFINITE'."
                    ) from exc
                raise
        if self.snap_start and not self.runtime.startswith("JAVA"):
            raise ValueError(
                f"function '{self.name}': snap_start is only supported for Java runtimes. "
                f"Got runtime: '{self.runtime}'"
            )
        if self.reserved_concurrent_executions < -1:
            raise ValueError(
                f"function '{self.name}': reserved_concurrent_executions must be >= -1. "
                f"Got: {self.reserved_concurrent_executions}"
            )

    @property
    def construct_id(self) -> str:
        """Safe CDK construct ID derived from the logical function name."""
        return self.name.replace("/", "-").replace("_", "-")


# ── Top-level Lambda config ────────────────────────────────────────────────────

@dataclass
class LambdaConfig(BaseConfig):
    """
    Top-level config for the Lambda stack.

    Holds layers (created first so functions can reference them) and the
    list of function configs.

    Fields:
        layers:    Lambda Layer definitions (created before functions).
        functions: Lambda Function definitions.
    """

    layers: list[LambdaLayerConfig] = field(default_factory=list)
    functions: list[LambdaFunctionConfig] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        if not self.functions:
            raise ValueError("'lambda.functions' must contain at least one entry.")

        fn_names = [f.name for f in self.functions]
        dup_fns = {n for n in fn_names if fn_names.count(n) > 1}
        if dup_fns:
            raise ValueError(f"Duplicate function names found: {dup_fns}.")

        layer_names = [l.name for l in self.layers]
        dup_layers = {n for n in layer_names if layer_names.count(n) > 1}
        if dup_layers:
            raise ValueError(f"Duplicate layer names found: {dup_layers}.")

        for layer in self.layers:
            layer.validate()
        for fn in self.functions:
            fn.validate()

    @classmethod
    def from_dict(cls, project: str, environment: str, region: str, raw: dict) -> "LambdaConfig":
        layers = [cls._parse_layer(l) for l in raw.get("layers", [])]
        functions = [cls._parse_function(f) for f in raw.get("functions", [])]
        return cls(
            project=project,
            environment=environment,
            region=region,
            layers=layers,
            functions=functions,
        )

    # ── Static parsers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_code(raw: Optional[dict]) -> Optional[LambdaCodeConfig]:
        if not raw:
            return None
        return LambdaCodeConfig(
            type=raw.get("type", "S3"),
            s3_bucket=raw.get("s3_bucket", ""),
            s3_key=raw.get("s3_key", ""),
            s3_object_version=raw.get("s3_object_version", ""),
            inline_code=raw.get("inline_code", ""),
            ecr_repo_arn=raw.get("ecr_repo_arn", ""),
            image_tag=raw.get("image_tag", "latest"),
            image_cmd=raw.get("image_cmd", []),
            image_entrypoint=raw.get("image_entrypoint", []),
            image_working_directory=raw.get("image_working_directory", ""),
        )

    @staticmethod
    def _parse_vpc(raw: Optional[dict]) -> Optional[LambdaVpcConfig]:
        if not raw:
            return None
        return LambdaVpcConfig(
            vpc_id=raw.get("vpc_id", ""),
            subnet_ids=raw.get("subnet_ids", []),
            security_group_ids=raw.get("security_group_ids", []),
        )

    @staticmethod
    def _parse_dlq(raw: Optional[dict]) -> Optional[LambdaDlqConfig]:
        if not raw:
            return None
        return LambdaDlqConfig(type=raw.get("type", "SQS"), arn=raw.get("arn", ""))

    @staticmethod
    def _parse_destination(raw: Optional[dict]) -> Optional[LambdaDestinationConfig]:
        if not raw:
            return None
        return LambdaDestinationConfig(type=raw.get("type", "SQS"), arn=raw.get("arn", ""))

    @staticmethod
    def _parse_function_url(raw: Optional[dict]) -> Optional[FunctionUrlConfig]:
        if not raw or not raw.get("enabled", False):
            return None
        cors_raw = raw.get("cors")
        cors = None
        if cors_raw:
            cors = FunctionUrlCorsConfig(
                allow_origins=cors_raw.get("allow_origins", ["*"]),
                allow_methods=cors_raw.get("allow_methods", ["*"]),
                allow_headers=cors_raw.get("allow_headers", []),
                expose_headers=cors_raw.get("expose_headers", []),
                max_age=cors_raw.get("max_age", 0),
            )
        return FunctionUrlConfig(
            enabled=True,
            auth_type=raw.get("auth_type", "NONE"),
            cors=cors,
        )

    @classmethod
    def _parse_layer(cls, raw: dict) -> LambdaLayerConfig:
        return LambdaLayerConfig(
            name=raw["name"],
            description=raw.get("description", ""),
            compatible_runtimes=raw.get("compatible_runtimes", []),
            compatible_architectures=raw.get("compatible_architectures", []),
            removal_policy=raw.get("removal_policy", "RETAIN"),
            license=raw.get("license", ""),
            packages=raw.get("packages", []),
            build_runtime=raw.get("build_runtime", ""),
            code=cls._parse_code(raw.get("code")),
            layer_version_arn=raw.get("layer_version_arn", ""),
        )

    @classmethod
    def _parse_function(cls, raw: dict) -> LambdaFunctionConfig:
        aliases = [
            LambdaAliasConfig(
                name=a["name"],
                description=a.get("description", ""),
                provisioned_concurrent_executions=a.get(
                    "provisioned_concurrent_executions", 0
                ),
            )
            for a in raw.get("aliases", [])
        ]
        return LambdaFunctionConfig(
            name=raw["name"],
            description=raw.get("description", ""),
            handler=raw.get("handler", "app.handler"),
            runtime=raw.get("runtime", "PYTHON_3_11"),
            memory=raw.get("memory", 128),
            timeout=raw.get("timeout", 30),
            architecture=raw.get("architecture", "X86_64"),
            ephemeral_storage_size=raw.get("ephemeral_storage_size", 512),
            code=cls._parse_code(raw.get("code")),
            role_arn=raw.get("role_arn", ""),
            environment=raw.get("environment", {}),
            layers=raw.get("layers", []),
            vpc=cls._parse_vpc(raw.get("vpc")),
            reserved_concurrent_executions=raw.get("reserved_concurrent_executions", -1),
            dead_letter_queue=cls._parse_dlq(raw.get("dead_letter_queue")),
            on_success=cls._parse_destination(raw.get("on_success")),
            on_failure=cls._parse_destination(raw.get("on_failure")),
            tracing=raw.get("tracing", "DISABLED"),
            log_format=raw.get("log_format", "TEXT"),
            log_retention=raw.get("log_retention", 30),
            snap_start=raw.get("snap_start", False),
            function_url=cls._parse_function_url(raw.get("function_url")),
            aliases=aliases,
            tags=raw.get("tags", {}),
        )
