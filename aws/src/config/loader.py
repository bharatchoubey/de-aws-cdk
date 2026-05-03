from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from config.base import BaseConfigLoader
from config.models.base import BaseConfig
from config.models.iam import IamConfig
from config.models.secrets_manager import SecretsManagerConfig
from config.models.ssm import SsmConfig
from logger import get_logger

log = get_logger(__name__)

_SERVICE_FACTORIES = {
    "ssm": SsmConfig.from_dict,
    "secrets_manager": SecretsManagerConfig.from_dict,
    "iam": IamConfig.from_dict,
}

_CONFIGS_ROOT = Path(__file__).parents[2] / "configs"


class YamlConfigLoader(BaseConfigLoader):
    """
    Loads service configuration from YAML files located at:

        configs/{env}/{service}.yaml

    The path root is resolved relative to the ``aws/`` directory so the
    loader works regardless of the working directory CDK is invoked from.
    """

    def __init__(self, configs_root: Path | None = None) -> None:
        self._configs_root = configs_root or _CONFIGS_ROOT

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, service: str, env: str) -> BaseConfig:
        """
        Load, validate, and return a typed config for *service* in *env*.

        Args:
            service: config file stem (e.g. 'ssm')
            env:     environment subdirectory (e.g. 'dev')

        Returns:
            A validated BaseConfig subclass.

        Raises:
            FileNotFoundError: if the config file does not exist.
            ValueError:        if the YAML structure is invalid.
            KeyError:          if *service* has no registered factory.
        """
        path = self._resolve_path(service, env)
        log.info("Loading config: service=%s env=%s path=%s", service, env, path)

        try:
            raw = self._read_file(str(path))
            self._validate(raw)

            factory = self._get_factory(service)
            environment = raw.get("environment", env)
            region = raw.get("region", "us-east-1")
            service_block = raw.get(service, {})

            config = factory(environment, region, service_block)
            log.debug("Config loaded successfully: service=%s env=%s region=%s", service, env, region)
            return config

        except FileNotFoundError:
            log.error("Config file not found: %s", path)
            raise
        except ValueError as exc:
            log.error("Invalid config for service=%s env=%s: %s", service, env, exc)
            raise
        except KeyError as exc:
            log.error("Unknown service '%s': %s", service, exc)
            raise
        except Exception as exc:
            log.exception("Unexpected error loading config for service=%s env=%s: %s", service, env, exc)
            raise

    # ------------------------------------------------------------------
    # Protected implementation (BaseConfigLoader contract)
    # ------------------------------------------------------------------

    def _read_file(self, path: str) -> dict:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {file_path}\n"
                f"Expected location: configs/{{env}}/{{service}}.yaml"
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
        for required in ("environment", "region"):
            if required not in data:
                raise ValueError(f"Config file is missing required top-level key: '{required}'")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, service: str, env: str) -> Path:
        return self._configs_root / env / f"{service}.yaml"

    @staticmethod
    def _get_factory(service: str):
        if service not in _SERVICE_FACTORIES:
            supported = ", ".join(sorted(_SERVICE_FACTORIES))
            raise KeyError(
                f"No config factory registered for service '{service}'. "
                f"Supported: [{supported}]"
            )
        return _SERVICE_FACTORIES[service]


# YamlConfigLoader().load("ssm", "dev")