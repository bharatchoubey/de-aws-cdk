from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BaseConfig:
    """
    Root configuration shared by every AWS service config.

    Subclasses must call super().validate() before their own checks
    so that environment and region are always guaranteed present.
    """

    environment: str
    region: str

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.environment or not isinstance(self.environment, str):
            raise ValueError("'environment' must be a non-empty string.")
        if not self.region or not isinstance(self.region, str):
            raise ValueError("'region' must be a non-empty string.")
