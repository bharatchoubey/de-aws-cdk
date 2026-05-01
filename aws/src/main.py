from __future__ import annotations

import os

import aws_cdk as cdk

from config.loader import YamlConfigLoader
from config.models.secrets_manager import SecretsManagerConfig
from config.models.ssm import SsmConfig
from stacks.secrets_manager_stack import SecretsManagerStack
from stacks.ssm_stack import SsmStack

ENV = os.environ.get("CDK_ENV", "dev")

app = cdk.App()
loader = YamlConfigLoader()

ssm_config: SsmConfig = loader.load("ssm", ENV)
SsmStack(app, ssm_config)

secrets_config: SecretsManagerConfig = loader.load("secrets_manager", ENV)
SecretsManagerStack(app, secrets_config)

app.synth()
