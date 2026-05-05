from __future__ import annotations

import aws_cdk.aws_s3 as s3
from constructs import Construct

from config.models.s3 import S3Config
from logger import get_logger
from services.s3.construct import S3BucketConstruct
from stacks.base import BaseServiceStack

log = get_logger(__name__)


class S3Stack(BaseServiceStack):
    """
    CDK Stack for AWS S3 Buckets.

    Reads the list of buckets from ``S3Config`` and creates one
    ``S3BucketConstruct`` per entry.  Each construct is responsible
    for its own CDK resource; this stack only orchestrates iteration.

    Creation order: buckets that are not log targets are still created in
    YAML order, but buckets declared as ``server_access_logs_bucket`` targets
    are created first so that CDK receives a real ``Bucket`` object (not an
    imported reference) and can automatically add the required S3
    log-delivery bucket policy.

    After each bucket is created its CDK object is stored in ``bucket_refs``
    under both the logical name (``config.name``) and the explicit bucket name
    (``config.bucket_name``). Subsequent constructs look up their
    ``server_access_logs_bucket`` value in this dict before falling back to
    ``Bucket.from_bucket_name()`` for external targets.

    Stack ID: ``{env}-s3-stack``  (e.g. ``dev-s3-stack``)
    """

    def __init__(self, scope: Construct, config: S3Config, **kwargs) -> None:
        super().__init__(scope, "s3", config, **kwargs)

    def _build(self) -> None:
        total = len(self._config.buckets)
        log.info("Building S3 stack: %d bucket(s) to provision", total)

        # Collect all names that are referenced as log-target buckets.
        log_targets = {
            b.server_access_logs_bucket
            for b in self._config.buckets
            if b.server_access_logs_bucket
        }

        # Sort: log-target buckets first so their CDK objects are available
        # in bucket_refs before the logging buckets are created.
        sorted_buckets = sorted(
            self._config.buckets,
            key=lambda b: 0 if (b.name in log_targets or b.bucket_name in log_targets) else 1,
        )

        bucket_refs: dict[str, s3.IBucket] = {}

        for bucket_config in sorted_buckets:
            log.debug(
                "Creating S3 bucket: name=%s encryption=%s versioned=%s",
                bucket_config.name,
                bucket_config.encryption,
                bucket_config.versioned,
            )
            try:
                construct = S3BucketConstruct(self, bucket_config, bucket_refs, name_prefix=self._config.project)
                # Register under logical name so same-stack log targets resolve correctly.
                bucket_refs[bucket_config.name] = construct.bucket_resource
                if bucket_config.bucket_name:
                    bucket_refs[bucket_config.bucket_name] = construct.bucket_resource
            except Exception as exc:
                log.error("Failed to create S3 bucket '%s': %s", bucket_config.name, exc)
                raise

        log.info("S3 stack build complete: %d bucket(s) defined", total)
