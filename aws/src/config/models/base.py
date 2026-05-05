from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BaseConfig:
    """
    Root configuration shared by every AWS service config.

    Subclasses must call super().validate() before their own checks
    so that project, environment, and region are always guaranteed present.

    Fields:
        project:     Short identifier for the project that owns these resources.
                     Included in every stack ID and every CDK construct ID to
                     prevent naming conflicts when multiple projects deploy from
                     the same CDK module.
                     Example: 'myapp', 'platform', 'data-pipeline'
        environment: Deployment environment (e.g. 'dev', 'staging', 'prod').
        region:      AWS region for the stack (e.g. 'us-east-1').
    """

    project: str
    environment: str
    region: str

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.project or not isinstance(self.project, str):
            raise ValueError("'project' must be a non-empty string.")
        if not self.environment or not isinstance(self.environment, str):
            raise ValueError("'environment' must be a non-empty string.")
        if not self.region or not isinstance(self.region, str):
            raise ValueError("'region' must be a non-empty string.")
