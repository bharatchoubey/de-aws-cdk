from __future__ import annotations

import os
import sys

import aws_cdk as cdk

from config.loader import YamlConfigLoader
from config.models.iam import IamConfig
from config.models.s3 import S3Config
from config.models.secrets_manager import SecretsManagerConfig
from config.models.ssm import SsmConfig
from logger import get_logger
from stacks.iam_stack import IamStack
from stacks.s3_stack import S3Stack
from stacks.secrets_manager_stack import SecretsManagerStack
from stacks.ssm_stack import SsmStack

log = get_logger(__name__)

# Config path: configs/{CDK_ENV}/{CDK_PROJECT}/{CDK_REGION}/{service}.yaml
ENV = os.environ.get("CDK_ENV", "dev")
PROJECT = os.environ.get("CDK_PROJECT", "myapp")
REGION = os.environ.get("CDK_REGION", "us-east-1")

log.info(
    "Starting CDK synthesis (CDK_ENV=%s CDK_PROJECT=%s CDK_REGION=%s)",
    ENV, PROJECT, REGION,
)

try:
    app = cdk.App()
    loader = YamlConfigLoader()

    ssm_config: SsmConfig = loader.load("ssm", ENV, PROJECT, REGION)
    SsmStack(app, ssm_config)

    secrets_config: SecretsManagerConfig = loader.load("secrets_manager", ENV, PROJECT, REGION)
    SecretsManagerStack(app, secrets_config)

    iam_config: IamConfig = loader.load("iam", ENV, PROJECT, REGION)
    IamStack(app, iam_config)

    s3_config: S3Config = loader.load("s3", ENV, PROJECT, REGION)
    S3Stack(app, s3_config)

    log.info("All stacks synthesized successfully")
    app.synth()

except (FileNotFoundError, ValueError, KeyError, EnvironmentError) as exc:
    log.error("Synthesis failed: %s", exc)
    sys.exit(1)
except Exception as exc:
    log.exception("Unexpected error during synthesis: %s", exc)
    sys.exit(1)
