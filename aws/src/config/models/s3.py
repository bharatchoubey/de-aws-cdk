from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from config.models.base import BaseConfig

# ── Validation sets ────────────────────────────────────────────────────────────

VALID_REMOVAL_POLICIES = {"DESTROY", "RETAIN", "SNAPSHOT"}

VALID_ENCRYPTION_MODES = {
    "S3_MANAGED",    # SSE-S3  (AES-256, AWS-managed key)
    "KMS_MANAGED",   # SSE-KMS with AWS-managed key (free tier)
    "KMS",           # SSE-KMS with customer-managed key (requires encryption_key_arn)
    "DSSE_MANAGED",  # Dual-layer SSE-KMS, AWS-managed key
    "DSSE",          # Dual-layer SSE-KMS, customer-managed key (requires encryption_key_arn)
    "UNENCRYPTED",   # No server-side encryption (not recommended)
}

VALID_BLOCK_PUBLIC_ACCESS = {
    "BLOCK_ALL",   # All four public-access settings enabled
    "BLOCK_ACLS",  # Only ACL-based public access blocked
    "NONE",        # No block (needed for public-facing / static-website buckets)
}

VALID_OBJECT_OWNERSHIP = {
    "BUCKET_OWNER_ENFORCED",   # ACLs disabled; bucket owner owns everything
    "BUCKET_OWNER_PREFERRED",  # Bucket owner owns new objects if ACL grants ownership
    "OBJECT_WRITER",           # Object uploader owns the object
}

VALID_HTTP_METHODS = {"GET", "PUT", "POST", "DELETE", "HEAD"}

VALID_STORAGE_CLASSES = {
    "GLACIER",              # S3 Glacier Flexible Retrieval  (min 90 days)
    "GLACIER_INSTANT_RETRIEVAL",  # S3 Glacier Instant Retrieval (min 90 days)
    "INTELLIGENT_TIERING",  # S3 Intelligent-Tiering          (min 0 days)
    "ONEZONE_IA",           # S3 One Zone-IA                  (min 30 days)
    "STANDARD_IA",          # S3 Standard-IA                  (min 30 days)
    "DEEP_ARCHIVE",         # S3 Glacier Deep Archive         (min 180 days)
}


# ── Sub-configs ────────────────────────────────────────────────────────────────

@dataclass
class LifecycleTransitionConfig:
    """
    Transitions objects to a different storage class after a number of days.

    Fields:
        storage_class:    Target storage class (see VALID_STORAGE_CLASSES).
        transition_after: Days after object creation before the transition.
    """

    storage_class: str
    transition_after: int

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.storage_class not in VALID_STORAGE_CLASSES:
            raise ValueError(
                f"Lifecycle transition 'storage_class' must be one of "
                f"{VALID_STORAGE_CLASSES}. Got: '{self.storage_class}'"
            )
        if self.transition_after < 0:
            raise ValueError(
                f"Lifecycle 'transition_after' must be >= 0. Got: {self.transition_after}"
            )


@dataclass
class LifecycleRuleConfig:
    """
    A single S3 lifecycle rule controlling object expiration and transitions.

    Fields:
        id:                                   Human-readable rule identifier.
        enabled:                              Whether the rule is active.
        prefix:                               Restrict the rule to object keys with this prefix.
        expiration:                           Permanently delete current objects after N days (0 = disabled).
        noncurrent_version_expiration:        Permanently delete non-current versions after N days (0 = disabled).
        abort_incomplete_multipart_upload_after: Abort incomplete uploads after N days (0 = disabled).
        transitions:                          Move current objects to cheaper storage tiers.
        noncurrent_version_transitions:       Move non-current versions to cheaper storage tiers.
    """

    id: str = ""
    enabled: bool = True
    prefix: str = ""
    expiration: int = 0
    noncurrent_version_expiration: int = 0
    abort_incomplete_multipart_upload_after: int = 0
    transitions: list[LifecycleTransitionConfig] = field(default_factory=list)
    noncurrent_version_transitions: list[LifecycleTransitionConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.expiration < 0:
            raise ValueError(f"Lifecycle 'expiration' must be >= 0. Got: {self.expiration}")
        if self.noncurrent_version_expiration < 0:
            raise ValueError(
                f"Lifecycle 'noncurrent_version_expiration' must be >= 0. "
                f"Got: {self.noncurrent_version_expiration}"
            )
        if self.abort_incomplete_multipart_upload_after < 0:
            raise ValueError(
                f"Lifecycle 'abort_incomplete_multipart_upload_after' must be >= 0. "
                f"Got: {self.abort_incomplete_multipart_upload_after}"
            )
        for t in self.transitions:
            t.validate()
        for t in self.noncurrent_version_transitions:
            t.validate()


@dataclass
class CorsRuleConfig:
    """
    A single CORS rule for the bucket.

    Required for browser-based uploads (S3 pre-signed URLs) and
    cross-origin web assets.

    Fields:
        allowed_methods:  HTTP methods to allow (GET, PUT, POST, DELETE, HEAD).
        allowed_origins:  Origins to allow (e.g. ['https://example.com'] or ['*']).
        allowed_headers:  Request headers to allow (e.g. ['Content-Type'] or ['*']).
        exposed_headers:  Response headers browsers are allowed to access.
        max_age:          How long (seconds) browsers may cache the preflight response.
        id:               Optional rule identifier.
    """

    allowed_methods: list[str]
    allowed_origins: list[str]
    allowed_headers: list[str] = field(default_factory=list)
    exposed_headers: list[str] = field(default_factory=list)
    max_age: int = 0
    id: str = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.allowed_methods:
            raise ValueError("CORS rule 'allowed_methods' must not be empty.")
        invalid = set(self.allowed_methods) - VALID_HTTP_METHODS
        if invalid:
            raise ValueError(
                f"CORS rule 'allowed_methods' contains invalid values: {invalid}. "
                f"Valid: {VALID_HTTP_METHODS}"
            )
        if not self.allowed_origins:
            raise ValueError("CORS rule 'allowed_origins' must not be empty.")
        if self.max_age < 0:
            raise ValueError(f"CORS rule 'max_age' must be >= 0. Got: {self.max_age}")


@dataclass
class IntelligentTieringConfig:
    """
    S3 Intelligent-Tiering configuration for auto-archiving infrequently accessed objects.

    Objects that have not been accessed for the configured number of days are
    automatically moved to the Archive Access or Deep Archive Access tier,
    reducing storage costs without requiring lifecycle rules.

    Fields:
        name:                          Unique name for this tiering configuration.
        archive_access_tier_time:      Move objects to Archive tier after N days (min 90, 0 = disabled).
        deep_archive_access_tier_time: Move objects to Deep Archive tier after N days (min 180, 0 = disabled).
        prefix:                        Restrict tiering to objects with this key prefix.
        tags:                          Restrict tiering to objects with these tags.
    """

    name: str
    archive_access_tier_time: int = 0
    deep_archive_access_tier_time: int = 0
    prefix: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Intelligent tiering 'name' must be a non-empty string.")
        if self.archive_access_tier_time and self.archive_access_tier_time < 90:
            raise ValueError(
                f"'archive_access_tier_time' must be >= 90 days. "
                f"Got: {self.archive_access_tier_time}"
            )
        if self.deep_archive_access_tier_time and self.deep_archive_access_tier_time < 180:
            raise ValueError(
                f"'deep_archive_access_tier_time' must be >= 180 days. "
                f"Got: {self.deep_archive_access_tier_time}"
            )


# ── Main bucket config ─────────────────────────────────────────────────────────

@dataclass
class S3BucketConfig:
    """
    Encapsulates all configuration for a single S3 bucket.

    Covers every CDK L2 ``aws_s3.Bucket`` feature:

    Storage & lifecycle:
        versioned:                    Enable object versioning (required for replication and MFA delete).
        removal_policy:               What happens to the bucket when the stack is destroyed.
        auto_delete_objects:          Empty and delete the bucket on DESTROY (requires removal_policy=DESTROY).
        lifecycle_rules:              Object expiration, storage-class transitions, multipart upload cleanup.
        intelligent_tiering:          Auto-archive infrequently accessed objects without lifecycle rules.

    Encryption:
        encryption:                   Server-side encryption mode.
        encryption_key_arn:           Customer-managed KMS key ARN (required for KMS and DSSE modes).
        bucket_key_enabled:           Reduce KMS API call costs by using a per-bucket S3 key.

    Access control:
        block_public_access:          Public access block setting (BLOCK_ALL recommended).
        public_read_access:           Allow unauthenticated GET requests (static website use case).
        object_ownership:             Who owns newly uploaded objects and whether ACLs are active.

    Static website hosting:
        website_index_document:       Default document for directory requests (e.g. 'index.html').
        website_error_document:       Returned on 4xx errors (e.g. 'error.html').

    Network & performance:
        transfer_acceleration:        Enable S3 Transfer Acceleration (CloudFront edge upload path).

    Events:
        event_bridge_enabled:         Emit all bucket events to Amazon EventBridge.

    Observability:
        server_access_logs_bucket:    Name of the target bucket that receives access logs.
        server_access_logs_prefix:    Key prefix for access log objects in the target bucket.

    Other:
        cors_rules:                   CORS configuration for browser-based uploads and web assets.
        bucket_name:                  Explicit bucket name (omit to let CloudFormation generate one).
        description:                  Free-text note for documentation purposes.
        tags:                         Resource tags applied to the bucket.
    """

    name: str
    bucket_name: str = ""
    description: str = ""
    removal_policy: str = "RETAIN"
    auto_delete_objects: bool = False
    versioned: bool = False

    # Encryption
    encryption: str = "S3_MANAGED"
    encryption_key_arn: str = ""
    bucket_key_enabled: bool = False

    # Access control
    block_public_access: str = "BLOCK_ALL"
    public_read_access: bool = False
    object_ownership: str = "BUCKET_OWNER_ENFORCED"

    # Static website hosting
    website_index_document: str = ""
    website_error_document: str = ""

    # Network
    transfer_acceleration: bool = False

    # Events
    event_bridge_enabled: bool = False

    # Server access logging
    server_access_logs_bucket: str = ""
    server_access_logs_prefix: str = ""

    # Complex sub-configurations
    lifecycle_rules: list[LifecycleRuleConfig] = field(default_factory=list)
    cors_rules: list[CorsRuleConfig] = field(default_factory=list)
    intelligent_tiering: list[IntelligentTieringConfig] = field(default_factory=list)

    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("S3 bucket 'name' must be a non-empty string.")
        if self.removal_policy not in VALID_REMOVAL_POLICIES:
            raise ValueError(
                f"S3 bucket '{self.name}' 'removal_policy' must be one of "
                f"{VALID_REMOVAL_POLICIES}. Got: '{self.removal_policy}'"
            )
        if self.auto_delete_objects and self.removal_policy != "DESTROY":
            raise ValueError(
                f"S3 bucket '{self.name}': 'auto_delete_objects' can only be true "
                f"when 'removal_policy' is 'DESTROY'. Got: '{self.removal_policy}'"
            )
        if self.encryption not in VALID_ENCRYPTION_MODES:
            raise ValueError(
                f"S3 bucket '{self.name}' 'encryption' must be one of "
                f"{VALID_ENCRYPTION_MODES}. Got: '{self.encryption}'"
            )
        if self.encryption in {"KMS", "DSSE"} and not self.encryption_key_arn:
            raise ValueError(
                f"S3 bucket '{self.name}': 'encryption_key_arn' is required when "
                f"'encryption' is '{self.encryption}'."
            )
        if self.encryption_key_arn and self.encryption not in {"KMS", "DSSE"}:
            raise ValueError(
                f"S3 bucket '{self.name}': 'encryption_key_arn' is only valid when "
                f"'encryption' is 'KMS' or 'DSSE'. Got: '{self.encryption}'"
            )
        if self.block_public_access not in VALID_BLOCK_PUBLIC_ACCESS:
            raise ValueError(
                f"S3 bucket '{self.name}' 'block_public_access' must be one of "
                f"{VALID_BLOCK_PUBLIC_ACCESS}. Got: '{self.block_public_access}'"
            )
        if self.object_ownership not in VALID_OBJECT_OWNERSHIP:
            raise ValueError(
                f"S3 bucket '{self.name}' 'object_ownership' must be one of "
                f"{VALID_OBJECT_OWNERSHIP}. Got: '{self.object_ownership}'"
            )
        if self.public_read_access and self.block_public_access == "BLOCK_ALL":
            raise ValueError(
                f"S3 bucket '{self.name}': 'public_read_access' cannot be true when "
                f"'block_public_access' is 'BLOCK_ALL'."
            )
        if self.bucket_key_enabled and self.encryption not in {"KMS", "KMS_MANAGED", "DSSE", "DSSE_MANAGED"}:
            raise ValueError(
                f"S3 bucket '{self.name}': 'bucket_key_enabled' is only valid for KMS "
                f"or DSSE encryption modes. Got: '{self.encryption}'"
            )
        if self.website_error_document and not self.website_index_document:
            raise ValueError(
                f"S3 bucket '{self.name}': 'website_error_document' requires "
                f"'website_index_document' to also be set."
            )
        for rule in self.lifecycle_rules:
            rule.validate()
        for rule in self.cors_rules:
            rule.validate()
        for tier in self.intelligent_tiering:
            tier.validate()

    @property
    def construct_id(self) -> str:
        """Returns a safe CDK construct ID derived from the logical bucket name."""
        return self.name.replace("/", "-").replace("_", "-")


# ── Top-level S3 config ────────────────────────────────────────────────────────

@dataclass
class S3Config(BaseConfig):
    """
    Top-level config for the S3 stack.

    Holds the list of S3BucketConfig objects parsed from
    the YAML 's3.buckets' block.
    """

    buckets: list[S3BucketConfig] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        if not self.buckets:
            raise ValueError("'s3.buckets' must contain at least one entry.")
        names = [b.name for b in self.buckets]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate bucket names found: {duplicates}. Each bucket name must be unique."
            )
        for bucket in self.buckets:
            bucket.validate()

    @classmethod
    def from_dict(cls, project: str, environment: str, region: str, raw: dict) -> "S3Config":
        raw_buckets = raw.get("buckets", [])
        buckets = [cls._parse_bucket(b) for b in raw_buckets]
        return cls(project=project, environment=environment, region=region, buckets=buckets)

    @staticmethod
    def _parse_lifecycle_transition(raw: dict) -> LifecycleTransitionConfig:
        return LifecycleTransitionConfig(
            storage_class=raw["storage_class"],
            transition_after=raw["transition_after"],
        )

    @classmethod
    def _parse_lifecycle_rule(cls, raw: dict) -> LifecycleRuleConfig:
        return LifecycleRuleConfig(
            id=raw.get("id", ""),
            enabled=raw.get("enabled", True),
            prefix=raw.get("prefix", ""),
            expiration=raw.get("expiration", 0),
            noncurrent_version_expiration=raw.get("noncurrent_version_expiration", 0),
            abort_incomplete_multipart_upload_after=raw.get(
                "abort_incomplete_multipart_upload_after", 0
            ),
            transitions=[
                cls._parse_lifecycle_transition(t)
                for t in raw.get("transitions", [])
            ],
            noncurrent_version_transitions=[
                cls._parse_lifecycle_transition(t)
                for t in raw.get("noncurrent_version_transitions", [])
            ],
        )

    @staticmethod
    def _parse_cors_rule(raw: dict) -> CorsRuleConfig:
        return CorsRuleConfig(
            allowed_methods=raw["allowed_methods"],
            allowed_origins=raw["allowed_origins"],
            allowed_headers=raw.get("allowed_headers", []),
            exposed_headers=raw.get("exposed_headers", []),
            max_age=raw.get("max_age", 0),
            id=raw.get("id", ""),
        )

    @staticmethod
    def _parse_intelligent_tiering(raw: dict) -> IntelligentTieringConfig:
        return IntelligentTieringConfig(
            name=raw["name"],
            archive_access_tier_time=raw.get("archive_access_tier_time", 0),
            deep_archive_access_tier_time=raw.get("deep_archive_access_tier_time", 0),
            prefix=raw.get("prefix", ""),
            tags=raw.get("tags", {}),
        )

    @classmethod
    def _parse_bucket(cls, raw: dict) -> S3BucketConfig:
        return S3BucketConfig(
            name=raw["name"],
            bucket_name=raw.get("bucket_name", ""),
            description=raw.get("description", ""),
            removal_policy=raw.get("removal_policy", "RETAIN"),
            auto_delete_objects=raw.get("auto_delete_objects", False),
            versioned=raw.get("versioned", False),
            encryption=raw.get("encryption", "S3_MANAGED"),
            encryption_key_arn=raw.get("encryption_key_arn", ""),
            bucket_key_enabled=raw.get("bucket_key_enabled", False),
            block_public_access=raw.get("block_public_access", "BLOCK_ALL"),
            public_read_access=raw.get("public_read_access", False),
            object_ownership=raw.get("object_ownership", "BUCKET_OWNER_ENFORCED"),
            website_index_document=raw.get("website_index_document", ""),
            website_error_document=raw.get("website_error_document", ""),
            transfer_acceleration=raw.get("transfer_acceleration", False),
            event_bridge_enabled=raw.get("event_bridge_enabled", False),
            server_access_logs_bucket=raw.get("server_access_logs_bucket", ""),
            server_access_logs_prefix=raw.get("server_access_logs_prefix", ""),
            lifecycle_rules=[
                cls._parse_lifecycle_rule(r) for r in raw.get("lifecycle_rules", [])
            ],
            cors_rules=[
                cls._parse_cors_rule(r) for r in raw.get("cors_rules", [])
            ],
            intelligent_tiering=[
                cls._parse_intelligent_tiering(t)
                for t in raw.get("intelligent_tiering", [])
            ],
            tags=raw.get("tags", {}),
        )
