from __future__ import annotations

from typing import Optional

import aws_cdk as cdk
import aws_cdk.aws_kms as kms
import aws_cdk.aws_s3 as s3
from constructs import Construct

from config.models.s3 import (
    CorsRuleConfig,
    IntelligentTieringConfig,
    LifecycleRuleConfig,
    S3BucketConfig,
)
from logger import get_logger
from services.base import BaseServiceConstruct

log = get_logger(__name__)

# ── Mapping tables ─────────────────────────────────────────────────────────────

_ENCRYPTION_MAP = {
    "S3_MANAGED": s3.BucketEncryption.S3_MANAGED,
    "KMS_MANAGED": s3.BucketEncryption.KMS_MANAGED,
    "KMS": s3.BucketEncryption.KMS,
    "DSSE_MANAGED": s3.BucketEncryption.DSSE_MANAGED,
    "DSSE": s3.BucketEncryption.DSSE,
    "UNENCRYPTED": s3.BucketEncryption.UNENCRYPTED,
}

_REMOVAL_POLICY_MAP = {
    "DESTROY": cdk.RemovalPolicy.DESTROY,
    "RETAIN": cdk.RemovalPolicy.RETAIN,
    "SNAPSHOT": cdk.RemovalPolicy.SNAPSHOT,
}

_STORAGE_CLASS_MAP = {
    "GLACIER": s3.StorageClass.GLACIER,
    "GLACIER_INSTANT_RETRIEVAL": s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
    "INTELLIGENT_TIERING": s3.StorageClass.INTELLIGENT_TIERING,
    "ONEZONE_IA": s3.StorageClass.ONE_ZONE_INFREQUENT_ACCESS,
    "STANDARD_IA": s3.StorageClass.INFREQUENT_ACCESS,
    "DEEP_ARCHIVE": s3.StorageClass.DEEP_ARCHIVE,
}

_HTTP_METHODS_MAP = {
    "GET": s3.HttpMethods.GET,
    "PUT": s3.HttpMethods.PUT,
    "POST": s3.HttpMethods.POST,
    "DELETE": s3.HttpMethods.DELETE,
    "HEAD": s3.HttpMethods.HEAD,
}

_OBJECT_OWNERSHIP_MAP = {
    "BUCKET_OWNER_ENFORCED": s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
    "BUCKET_OWNER_PREFERRED": s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
    "OBJECT_WRITER": s3.ObjectOwnership.OBJECT_WRITER,
}


class S3BucketConstruct(BaseServiceConstruct):
    """
    CDK Construct for a single S3 bucket with full feature coverage.

    Supports all CDK L2 ``aws_s3.Bucket`` features:
      - Encryption (S3_MANAGED, KMS, KMS_MANAGED, DSSE, DSSE_MANAGED, UNENCRYPTED)
      - Versioning
      - Lifecycle rules (expiration, storage-class transitions, noncurrent versions)
      - CORS rules
      - S3 Intelligent-Tiering configurations
      - Block public access and object ownership
      - Static website hosting
      - Transfer acceleration
      - EventBridge notifications
      - Server access logging

    ``bucket_refs`` maps logical bucket names (and explicit bucket_name values) to
    already-created CDK ``IBucket`` objects within the same stack.  When
    ``server_access_logs_bucket`` matches a key in this dict the real CDK object is
    used so that CDK can automatically add the required S3-log-delivery bucket
    policy.  Unknown names fall back to ``Bucket.from_bucket_name()`` (external
    buckets), which produces a warning because CDK cannot mutate their policies.

    Exposes ``bucket_resource`` so the S3Stack can collect references for
    subsequent constructs (same pattern as ``IamGroupConstruct.group_resource``).

    Inherits from ``BaseServiceConstruct`` which guarantees
    ``_create_resource()`` is called automatically during construction.
    """

    def __init__(
        self,
        scope: Construct,
        config: S3BucketConfig,
        bucket_refs: dict[str, s3.IBucket] | None = None,
        name_prefix: str = "",
    ) -> None:
        self.bucket_resource: s3.IBucket | None = None
        self._bucket_refs = bucket_refs or {}
        cid = f"{name_prefix}-{config.construct_id}" if name_prefix else config.construct_id
        super().__init__(scope, cid, config)

    def _create_resource(self) -> None:
        config: S3BucketConfig = self._config

        try:
            encryption_key = self._resolve_encryption_key(config)
            block_public_access = self._resolve_block_public_access(config)
            lifecycle_rules = self._build_lifecycle_rules(config)
            cors_rules = self._build_cors_rules(config)
            intelligent_tiering = self._build_intelligent_tiering(config)
            server_access_logs = self._resolve_server_access_logs(config)

            bucket = s3.Bucket(
                self,
                "Resource",
                bucket_name=config.bucket_name or None,
                versioned=config.versioned,
                auto_delete_objects=config.auto_delete_objects,
                removal_policy=_REMOVAL_POLICY_MAP[config.removal_policy],
                encryption=_ENCRYPTION_MAP[config.encryption],
                encryption_key=encryption_key,
                bucket_key_enabled=config.bucket_key_enabled or None,
                block_public_access=block_public_access,
                public_read_access=config.public_read_access,
                object_ownership=_OBJECT_OWNERSHIP_MAP[config.object_ownership],
                website_index_document=config.website_index_document or None,
                website_error_document=config.website_error_document or None,
                transfer_acceleration=config.transfer_acceleration,
                event_bridge_enabled=config.event_bridge_enabled,
                server_access_logs_bucket=server_access_logs,
                server_access_logs_prefix=config.server_access_logs_prefix or None,
                lifecycle_rules=lifecycle_rules or None,
                cors=cors_rules or None,
                intelligent_tiering_configurations=intelligent_tiering or None,
            )

            self.bucket_resource = bucket

            for key, value in config.tags.items():
                cdk.Tags.of(bucket).add(key, value)

            log.debug(
                "S3 bucket created: name=%s encryption=%s versioned=%s",
                config.name,
                config.encryption,
                config.versioned,
            )

        except Exception as exc:
            log.error("Failed to create S3 bucket '%s': %s", config.name, exc)
            raise

    # ── Private helpers ────────────────────────────────────────────────────────

    def _resolve_encryption_key(self, config: S3BucketConfig) -> Optional[kms.IKey]:
        if not config.encryption_key_arn:
            return None
        return kms.Key.from_key_arn(self, "KmsKey", config.encryption_key_arn)

    @staticmethod
    def _resolve_block_public_access(config: S3BucketConfig) -> s3.BlockPublicAccess:
        if config.block_public_access == "BLOCK_ALL":
            return s3.BlockPublicAccess.BLOCK_ALL
        if config.block_public_access == "BLOCK_ACLS":
            return s3.BlockPublicAccess.BLOCK_ACLS
        # NONE — explicitly disable all four public-access restrictions so that
        # public_read_access and static website hosting work correctly.
        # Must be explicit because the CDK feature flag
        # @aws-cdk/aws-s3:blockPublicAccessByDefault defaults to BLOCK_ALL.
        return s3.BlockPublicAccess(
            block_public_acls=False,
            block_public_policy=False,
            ignore_public_acls=False,
            restrict_public_buckets=False,
        )

    def _resolve_server_access_logs(self, config: S3BucketConfig) -> Optional[s3.IBucket]:
        if not config.server_access_logs_bucket:
            return None
        # Prefer a CDK-owned bucket from the same stack so CDK can automatically
        # add the S3 log-delivery bucket policy.  Fall back to an imported
        # reference for external buckets (produces a CDK warning that the policy
        # must be added manually).
        if config.server_access_logs_bucket in self._bucket_refs:
            log.debug(
                "Resolved server access logs target '%s' from stack bucket_refs",
                config.server_access_logs_bucket,
            )
            return self._bucket_refs[config.server_access_logs_bucket]
        log.warning(
            "server_access_logs_bucket '%s' for bucket '%s' is not defined in this "
            "stack — importing by name. CDK cannot add the log-delivery policy to "
            "an external bucket; ensure the policy is present on the target bucket.",
            config.server_access_logs_bucket,
            config.name,
        )
        return s3.Bucket.from_bucket_name(
            self, "AccessLogsBucket", config.server_access_logs_bucket
        )

    @staticmethod
    def _build_lifecycle_rules(config: S3BucketConfig) -> list[s3.LifecycleRule]:
        rules = []
        for rule_cfg in config.lifecycle_rules:
            rule_kwargs: dict = {
                "enabled": rule_cfg.enabled,
            }
            if rule_cfg.id:
                rule_kwargs["id"] = rule_cfg.id
            if rule_cfg.prefix:
                rule_kwargs["prefix"] = rule_cfg.prefix
            if rule_cfg.expiration:
                rule_kwargs["expiration"] = cdk.Duration.days(rule_cfg.expiration)
            if rule_cfg.noncurrent_version_expiration:
                rule_kwargs["noncurrent_version_expiration"] = cdk.Duration.days(
                    rule_cfg.noncurrent_version_expiration
                )
            if rule_cfg.abort_incomplete_multipart_upload_after:
                rule_kwargs["abort_incomplete_multipart_upload_after"] = cdk.Duration.days(
                    rule_cfg.abort_incomplete_multipart_upload_after
                )
            if rule_cfg.transitions:
                rule_kwargs["transitions"] = [
                    s3.Transition(
                        storage_class=_STORAGE_CLASS_MAP[t.storage_class],
                        transition_after=cdk.Duration.days(t.transition_after),
                    )
                    for t in rule_cfg.transitions
                ]
            if rule_cfg.noncurrent_version_transitions:
                rule_kwargs["noncurrent_version_transitions"] = [
                    s3.NoncurrentVersionTransition(
                        storage_class=_STORAGE_CLASS_MAP[t.storage_class],
                        transition_after=cdk.Duration.days(t.transition_after),
                    )
                    for t in rule_cfg.noncurrent_version_transitions
                ]
            rules.append(s3.LifecycleRule(**rule_kwargs))
        return rules

    @staticmethod
    def _build_cors_rules(config: S3BucketConfig) -> list[s3.CorsRule]:
        rules = []
        for cors_cfg in config.cors_rules:
            rule_kwargs: dict = {
                "allowed_methods": [_HTTP_METHODS_MAP[m] for m in cors_cfg.allowed_methods],
                "allowed_origins": cors_cfg.allowed_origins,
            }
            if cors_cfg.allowed_headers:
                rule_kwargs["allowed_headers"] = cors_cfg.allowed_headers
            if cors_cfg.exposed_headers:
                rule_kwargs["exposed_headers"] = cors_cfg.exposed_headers
            if cors_cfg.max_age:
                rule_kwargs["max_age"] = cors_cfg.max_age
            if cors_cfg.id:
                rule_kwargs["id"] = cors_cfg.id
            rules.append(s3.CorsRule(**rule_kwargs))
        return rules

    @staticmethod
    def _build_intelligent_tiering(
        config: S3BucketConfig,
    ) -> list[s3.IntelligentTieringConfiguration]:
        configs = []
        for tier_cfg in config.intelligent_tiering:
            tier_kwargs: dict = {"name": tier_cfg.name}
            if tier_cfg.archive_access_tier_time:
                tier_kwargs["archive_access_tier_time"] = cdk.Duration.days(
                    tier_cfg.archive_access_tier_time
                )
            if tier_cfg.deep_archive_access_tier_time:
                tier_kwargs["deep_archive_access_tier_time"] = cdk.Duration.days(
                    tier_cfg.deep_archive_access_tier_time
                )
            if tier_cfg.prefix:
                tier_kwargs["prefix"] = tier_cfg.prefix
            if tier_cfg.tags:
                tier_kwargs["tags"] = [
                    s3.Tag(key=key, value=value) for key, value in tier_cfg.tags.items()
                ]
            configs.append(s3.IntelligentTieringConfiguration(**tier_kwargs))
        return configs
