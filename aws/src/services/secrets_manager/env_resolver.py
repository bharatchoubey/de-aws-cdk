from __future__ import annotations

import os
import re
from typing import Union

from logger import get_logger

log = get_logger(__name__)

_TOKEN_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def resolve(value: Union[str, dict, None]) -> Union[str, dict, None]:
    """
    Recursively replace ``${VAR}`` tokens in *value* with environment variable values.

    Behaviour:
      - String values: all ``${VAR}`` tokens are replaced inline.
      - Dict values:   applied to each dict value recursively (keys are never replaced).
      - None:          returned unchanged (used for Generated/Reference types).

    Raises:
        EnvironmentError: immediately if any referenced variable is not set,
                          so failures surface at CDK synth time rather than
                          silently at runtime.

    Examples::

        os.environ["DB_PASS"] = "s3cr3t"
        resolve("${DB_PASS}")          # → "s3cr3t"
        resolve({"pw": "${DB_PASS}"})  # → {"pw": "s3cr3t"}
        resolve(None)                  # → None
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: resolve(v) for k, v in value.items()}
    if isinstance(value, str):
        try:
            return _resolve_string(value)
        except EnvironmentError:
            raise
        except Exception as exc:
            log.error("Unexpected error resolving env tokens in value: %s", exc)
            raise
    return value


def _resolve_string(value: str) -> str:
    tokens = _TOKEN_PATTERN.findall(value)
    if tokens:
        log.debug("Resolving %d env token(s): %s", len(tokens), tokens)

    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            log.error("Environment variable '%s' is not set", var_name)
            raise EnvironmentError(
                f"Environment variable '{var_name}' is not set. "
                f"Set it before running 'cdk synth' or 'cdk deploy'."
            )
        log.debug("Resolved env token: ${%s}", var_name)
        return env_value

    return _TOKEN_PATTERN.sub(_replace, value)
