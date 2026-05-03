from __future__ import annotations

import os
import sys

import aws_cdk as cdk

from config.loader import YamlConfigLoader
from config.models.iam import IamConfig
from config.models.secrets_manager import SecretsManagerConfig
from config.models.ssm import SsmConfig
from logger import get_logger
from stacks.iam_stack import IamStack
from stacks.secrets_manager_stack import SecretsManagerStack
from stacks.ssm_stack import SsmStack

log = get_logger(__name__)

ENV = os.environ.get("CDK_ENV", "dev")

log.info("Starting CDK synthesis (CDK_ENV=%s)", ENV)

try:
    app = cdk.App()
    loader = YamlConfigLoader()

    ssm_config: SsmConfig = loader.load("ssm", ENV)
    SsmStack(app, ssm_config)

    secrets_config: SecretsManagerConfig = loader.load("secrets_manager", ENV)
    SecretsManagerStack(app, secrets_config)

    iam_config: IamConfig = loader.load("iam", ENV)
    IamStack(app, iam_config)

    log.info("All stacks synthesized successfully")
    app.synth()

except (FileNotFoundError, ValueError, KeyError, EnvironmentError) as exc:
    log.error("Synthesis failed: %s", exc)
    sys.exit(1)
except Exception as exc:
    log.exception("Unexpected error during synthesis: %s", exc)
    sys.exit(1)
