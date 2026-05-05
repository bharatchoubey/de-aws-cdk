from __future__ import annotations

from pathlib import Path

import yaml

from config.base import BaseConfigLoader
from config.models.base import BaseConfig
from config.models.iam import IamConfig
from config.models.s3 import S3Config
from config.models.secrets_manager import SecretsManagerConfig
from config.models.ssm import SsmConfig
from logger import get_logger

log = get_logger(__name__)

_SERVICE_FACTORIES = {
    "ssm": SsmConfig.from_dict,
    "secrets_manager": SecretsManagerConfig.from_dict,
    "iam": IamConfig.from_dict,
    "s3": S3Config.from_dict,
}

_CONFIGS_ROOT = Path(__file__).parents[2] / "configs"


class YamlConfigLoader(BaseConfigLoader):
    """
    Loads service configuration from YAML files at:

        configs/{env}/{project}/{region}/{service}.yaml

    The path root is resolved relative to the ``aws/`` directory so the
    loader works regardless of the working directory CDK is invoked from.

    The directory path itself encodes ``env``, ``project``, and ``region`` —
    no metadata headers are needed inside the YAML files.  Each file contains
    only the service-specific resource declarations.
    """

    def __init__(self, configs_root: Path | None = None) -> None:
        self._configs_root = configs_root or _CONFIGS_ROOT

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, service: str, env: str, project: str, region: str) -> BaseConfig:
        """
        Load, validate, and return a typed config for the given combination.

        Args:
            service: config file stem (e.g. 'ssm')
            env:     environment directory   (e.g. 'dev')
            project: project directory       (e.g. 'myapp')
            region:  AWS region directory    (e.g. 'us-east-1')

        Returns:
            A validated BaseConfig subclass.

        Raises:
            FileNotFoundError: if the config file does not exist.
            ValueError:        if the YAML structure is invalid.
            KeyError:          if *service* has no registered factory.
        """
        path = self._resolve_path(service, env, project, region)
        log.info(
            "Loading config: service=%s env=%s project=%s region=%s path=%s",
            service, env, project, region, path,
        )

        try:
            raw = self._read_file(str(path))
            self._validate(raw)

            factory = self._get_factory(service)
            config = factory(project, env, region, raw)
            log.debug(
                "Config loaded successfully: service=%s project=%s env=%s region=%s",
                service, project, env, region,
            )
            return config

        except FileNotFoundError:
            log.error(
                "Config file not found: %s  "
                "(expected: configs/{env}/{project}/{region}/{service}.yaml)",
                path,
            )
            raise
        except ValueError as exc:
            log.error(
                "Invalid config for service=%s project=%s env=%s region=%s: %s",
                service, project, env, region, exc,
            )
            raise
        except KeyError as exc:
            log.error("Unknown service '%s': %s", service, exc)
            raise
        except Exception as exc:
            log.exception(
                "Unexpected error loading config for service=%s project=%s env=%s region=%s: %s",
                service, project, env, region, exc,
            )
            raise

    # ------------------------------------------------------------------
    # Protected implementation (BaseConfigLoader contract)
    # ------------------------------------------------------------------

    def _read_file(self, path: str) -> dict:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {file_path}\n"
                f"Expected location: configs/{{env}}/{{project}}/{{region}}/{{service}}.yaml"
            )
        try:
            with file_path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            log.debug("Read YAML file: %s", file_path)
        except yaml.YAMLError as exc:
            log.error("Failed to parse YAML file %s: %s", file_path, exc)
            raise ValueError(f"Failed to parse YAML file '{file_path}': {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"Config file must be a YAML mapping. Got: {type(data).__name__}")
        return data

    def _validate(self, data: dict) -> None:
        """
        Validate the raw YAML dict.

        The path structure (configs/{env}/{project}/{region}/{service}.yaml)
        encodes env, project, and region — those keys are not required inside
        the YAML content.  Only basic structural integrity is checked here;
        service-specific validation is handled by each config model.
        """
        if not data:
            raise ValueError("Config file is empty or contains no mappings.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, service: str, env: str, project: str, region: str) -> Path:
        """
        Resolve the YAML file path from its four path components.

        Structure: configs/{env}/{project}/{region}/{service}.yaml
        """
        return self._configs_root / env / project / region / f"{service}.yaml"

    @staticmethod
    def _get_factory(service: str):
        if service not in _SERVICE_FACTORIES:
            supported = ", ".join(sorted(_SERVICE_FACTORIES))
            raise KeyError(
                f"No config factory registered for service '{service}'. "
                f"Supported: [{supported}]"
            )
        return _SERVICE_FACTORIES[service]
