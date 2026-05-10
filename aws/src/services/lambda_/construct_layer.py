from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from typing import Optional

import aws_cdk as cdk
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_s3 as s3
import jsii
from constructs import Construct

from config.models.lambda_ import LambdaLayerConfig
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
}

_ARCHITECTURE_MAP: dict[str, lambda_.Architecture] = {
    "X86_64": lambda_.Architecture.X86_64,
    "ARM_64":  lambda_.Architecture.ARM_64,
}

_REMOVAL_POLICY_MAP: dict[str, cdk.RemovalPolicy] = {
    "RETAIN":  cdk.RemovalPolicy.RETAIN,
    "DESTROY": cdk.RemovalPolicy.DESTROY,
}

# Runtime name prefixes used to detect language family for Docker install commands
_PYTHON_PREFIX = "PYTHON_"
_NODEJS_PREFIX = "NODEJS_"


class LambdaLayerConstruct(BaseServiceConstruct):
    """
    CDK Construct for a Lambda Layer Version.

    Three modes depending on the config:

    1. **packages** (``packages`` list + ``build_runtime`` provided):
       CDK installs the packages inside a Lambda-compatible Docker container at
       synth time using ``pip install`` (Python) or ``npm install`` (Node.js).
       Docker must be running on the machine executing ``cdk synth / cdk deploy``.
       The resulting zip is uploaded to CDK's asset S3 bucket automatically.

    2. **S3 pre-built zip** (``code`` block provided):
       Creates a new ``lambda_.LayerVersion`` from an S3 deployment package that
       you built and uploaded yourself.  No Docker required.

    3. **Existing layer reference** (``layer_version_arn`` provided):
       Imports the layer by ARN via ``LayerVersion.from_layer_version_arn()``.
       No new AWS resource is created; this just produces a CDK ``ILayerVersion``
       reference so functions in the same stack can depend on it.

    Exposes ``layer_resource`` so ``LambdaStack`` can build a ``layer_refs`` dict
    that functions resolve by logical name.

    Inherits from ``BaseServiceConstruct`` — ``_create_resource()`` is called
    automatically during construction.
    """

    def __init__(
        self,
        scope: Construct,
        config: LambdaLayerConfig,
        name_prefix: str = "",
    ) -> None:
        self.layer_resource: Optional[lambda_.ILayerVersion] = None
        cid = f"{name_prefix}-{config.construct_id}" if name_prefix else config.construct_id
        super().__init__(scope, cid, config)

    def _create_resource(self) -> None:
        config: LambdaLayerConfig = self._config

        try:
            if config.layer_version_arn:
                self._import_existing_layer(config)
            else:
                self._create_new_layer(config)
        except Exception as exc:
            log.error("Failed to create/import layer '%s': %s", config.name, exc)
            raise

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _import_existing_layer(self, config: LambdaLayerConfig) -> None:
        log.debug("Importing existing layer by ARN: %s", config.layer_version_arn)
        self.layer_resource = lambda_.LayerVersion.from_layer_version_arn(
            self, "Resource", config.layer_version_arn
        )

    def _create_new_layer(self, config: LambdaLayerConfig) -> None:
        if config.packages:
            code = self._build_code_from_packages(config)
        else:
            code = self._resolve_code_from_s3(config)

        compatible_runtimes = (
            [_RUNTIME_MAP[r] for r in config.compatible_runtimes]
            if config.compatible_runtimes
            else None
        )
        compatible_architectures = (
            [_ARCHITECTURE_MAP[a] for a in config.compatible_architectures]
            if config.compatible_architectures
            else None
        )

        layer = lambda_.LayerVersion(
            self,
            "Resource",
            layer_version_name=config.name,
            description=config.description or None,
            compatible_runtimes=compatible_runtimes,
            compatible_architectures=compatible_architectures,
            removal_policy=_REMOVAL_POLICY_MAP[config.removal_policy],
            license=config.license or None,
            code=code,
        )
        self.layer_resource = layer
        log.debug(
            "Lambda layer created: name=%s mode=%s compatible_runtimes=%s",
            config.name,
            "packages" if config.packages else "s3",
            config.compatible_runtimes,
        )

    def _resolve_code_from_s3(self, config: LambdaLayerConfig) -> lambda_.Code:
        code_cfg = config.code
        if code_cfg.type == "S3":
            bucket = s3.Bucket.from_bucket_name(self, "CodeBucket", code_cfg.s3_bucket)
            return lambda_.Code.from_bucket(
                bucket,
                code_cfg.s3_key,
                code_cfg.s3_object_version or None,
            )
        raise ValueError(
            f"Layer '{config.name}': code.type='{code_cfg.type}' is not supported for layers. "
            f"Use 'S3' (pre-built zip) or 'packages' (Docker install) to create a new layer, "
            f"or 'layer_version_arn' to reference an existing one."
        )

    def _build_code_from_packages(self, config: LambdaLayerConfig) -> lambda_.Code:
        """
        Install ``config.packages`` and return the result as a CDK asset.

        **Bundling strategy — local first, Docker fallback:**

        CDK tries the local bundler first.  If `pip` / `npm` is on the PATH it
        installs the packages directly into a temp directory without Docker.
        This is the fast path used in dev containers and CI runners where Docker
        is not available.

        If local bundling fails (tool not on PATH, non-zero exit, etc.) CDK
        automatically falls back to Docker using the Lambda-compatible image for
        ``build_runtime``.

        Package layout written to the output directory:
          Python  →  <output>/python/     (pip ``-t`` target)
          Node.js →  <output>/nodejs/     (npm ``--prefix``)

        The asset hash is derived from the sorted package list so CDK only
        re-bundles when the list actually changes.
        """
        runtime = _RUNTIME_MAP[config.build_runtime]
        packages = config.packages
        is_python = config.build_runtime.startswith(_PYTHON_PREFIX)

        # ── Docker (fallback) install command ──────────────────────────────────
        if is_python:
            docker_cmd = (
                "pip install " + " ".join(f'"{p}"' for p in packages)
                + " -t /asset-output/python"
                + " && find /asset-output -type d -name '__pycache__'"
                + " -exec rm -rf {} + 2>/dev/null; true"
            )
        else:
            docker_cmd = (
                "mkdir -p /asset-output/nodejs"
                + " && npm install " + " ".join(f'"{p}"' for p in packages)
                + " --prefix /asset-output/nodejs"
            )

        # ── Asset hash — keyed on package list only ────────────────────────────
        pkg_hash = hashlib.sha256(
            " ".join(sorted(packages)).encode()
        ).hexdigest()[:20]

        # Use this file's directory as the (minimal) source; the layer content
        # is written entirely by the bundling command, not from the source dir.
        source_path = os.path.dirname(os.path.abspath(__file__))

        log.debug(
            "Building layer '%s' (%s): packages=%s",
            config.name,
            config.build_runtime,
            packages,
        )

        return lambda_.Code.from_asset(
            source_path,
            bundling=cdk.BundlingOptions(
                image=runtime.bundling_image,
                command=["bash", "-c", docker_cmd],
                # Local bundler runs pip/npm directly — no Docker socket needed.
                local=_LocalPackageBundler(packages, is_python),
            ),
            asset_hash_type=cdk.AssetHashType.CUSTOM,
            asset_hash=f"{config.name}-{pkg_hash}",
        )


@jsii.implements(cdk.ILocalBundling)
class _LocalPackageBundler:
    """
    CDK ``ILocalBundling`` implementation that installs packages without Docker.

    CDK calls ``try_bundle`` before attempting Docker.  Returns ``True`` on
    success (Docker is skipped); returns ``False`` on any failure so CDK can
    fall back to Docker automatically.

    Python: runs ``pip install <packages> -t <output>/python``
    Node.js: runs ``npm install <packages> --prefix <output>/nodejs``
    """

    def __init__(self, packages: list[str], is_python: bool) -> None:
        self._packages = packages
        self._is_python = is_python

    # Extra directories searched for pip / npm in addition to PATH.
    # Covers common virtualenv, pyenv, nvm, and Cursor-server locations.
    _EXTRA_SEARCH_DIRS = [
        os.path.expanduser("~/.local/bin"),
        os.path.expanduser("~/.nvm/versions/node/*/bin"),
        "/usr/local/bin",
        "/usr/bin",
        # Cursor server bundles its own Node + npm
        "/home/vscode/.cursor-server/bin/lib/node_modules/npm/bin",
    ]

    def try_bundle(self, output_dir: str, *, options: Optional[cdk.BundlingOptions] = None) -> bool:  # noqa: ARG002
        try:
            tool = "pip" if self._is_python else "npm"
            exe = self._find_executable(tool)
            if exe is None:
                log.debug(
                    "Local bundler: '%s' not found on PATH or known locations; "
                    "falling back to Docker.",
                    tool,
                )
                return False

            if self._is_python:
                python_dir = os.path.join(output_dir, "python")
                os.makedirs(python_dir, exist_ok=True)
                cmd = [exe, "install", *self._packages, "-t", python_dir]
            else:
                nodejs_dir = os.path.join(output_dir, "nodejs")
                os.makedirs(nodejs_dir, exist_ok=True)
                cmd = [exe, "install", *self._packages, "--prefix", nodejs_dir]

            log.debug("Local bundler running: %s", " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                log.warning(
                    "Local bundler failed (will fall back to Docker):\n%s",
                    result.stderr,
                )
                return False

            log.debug("Local bundler succeeded for packages: %s", self._packages)
            return True

        except Exception as exc:
            log.warning("Local bundler unexpected error (%s); falling back to Docker.", exc)
            return False

    @classmethod
    def _find_executable(cls, name: str) -> Optional[str]:
        """Return the full path to ``name`` or ``None`` if not found anywhere."""
        # 1. Standard PATH lookup
        found = shutil.which(name)
        if found:
            return found
        # 2. Search extra directories (handles nvm / cursor-server / venv layouts)
        import glob as _glob
        for pattern in cls._EXTRA_SEARCH_DIRS:
            for candidate in _glob.glob(pattern):
                full = os.path.join(candidate, name)
                if os.path.isfile(full) and os.access(full, os.X_OK):
                    return full
        return None
