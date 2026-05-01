# aws — Config-Driven AWS Infrastructure (CDK)

A config-driven AWS infrastructure module built on **AWS CDK (Python)**. Define your AWS resources in YAML — the framework synthesises and deploys them via CloudFormation. Adding a new AWS service requires no changes to the core framework.

---

## Table of Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Configuration](#configuration)
- [Supported Services](#supported-services)
  - [SSM Parameter Store](#ssm-parameter-store)
- [Usage](#usage)
- [Extending — Adding a New Service](#extending--adding-a-new-service)
- [Design Principles](#design-principles)

---

## Architecture

```
YAML Config  →  Config Loader  →  CDK Stack  →  CDK Construct  →  AWS
```

Each AWS service follows the same layered pattern:

| Layer | Responsibility |
|---|---|
| `configs/{env}/{service}.yaml` | Declare what resources to create |
| `config/loader.py` | Parse and validate the YAML into typed models |
| `stacks/{service}_stack.py` | CDK Stack — iterates resources, delegates to constructs |
| `services/{service}/construct.py` | CDK Construct — one logical resource |
| `services/{service}/types/` | Strategy per resource sub-type |

---

## Project Structure

```
aws/
├── cdk.json                          # CDK app entry point
├── requirements.txt                  # Python dependencies
├── configs/
│   └── dev/
│       └── ssm.yaml                  # SSM config for dev environment
└── src/
    ├── main.py                       # CDK App — loads config, mounts stacks
    ├── config/
    │   ├── base.py                   # BaseConfigLoader (abstract)
    │   ├── loader.py                 # YamlConfigLoader
    │   └── models/
    │       ├── base.py               # BaseConfig dataclass
    │       └── ssm.py                # SsmConfig, SsmParameterConfig
    ├── stacks/
    │   ├── base.py                       # BaseServiceStack (abstract CDK Stack)
    │   ├── ssm_stack.py                  # SsmStack
    │   └── secrets_manager_stack.py      # SecretsManagerStack
    └── services/
        ├── base.py                       # BaseServiceConstruct (abstract CDK Construct)
        ├── ssm/
        │   ├── construct.py              # SsmParameterConstruct
        │   └── types/
        │       ├── base.py               # BaseSsmParameter (strategy ABC)
        │       ├── string.py             # StringParameter
        │       └── string_list.py        # StringListParameter
        └── secrets_manager/
            ├── construct.py              # SecretConstruct
            └── types/
                ├── base.py               # BaseSecretType (strategy ABC)
                ├── plain_text.py         # PlainTextSecret
                └── key_value.py          # KeyValueSecret
```

---

## Setup

The virtual environment is shared across all modules and lives at the project root.

```bash
# From the project root (de-aws-cdk/)
python -m venv .venv
source .venv/bin/activate

# Install all module dependencies
pip install -r aws/requirements.txt -r cas/requirements.txt
```

Install the AWS CDK CLI (required for deploy/diff commands):

```bash
npm install -g aws-cdk
```

---

## Configuration

Config files live at `configs/{env}/{service}.yaml`. The environment is selected at runtime via the `CDK_ENV` environment variable (default: `dev`).

### Top-level keys (all configs)

| Key | Required | Description |
|---|---|---|
| `environment` | Yes | Deployment environment name (e.g. `dev`, `prod`) |
| `region` | Yes | AWS region (e.g. `us-east-1`) |

### Adding a new environment

Create a new directory and copy an existing config:

```bash
mkdir configs/prod
cp configs/dev/ssm.yaml configs/prod/ssm.yaml
# Edit configs/prod/ssm.yaml with prod values
```

Deploy to prod:

```bash
CDK_ENV=prod cdk deploy --all
```

---

## Supported Services

### SSM Parameter Store (non-sensitive config)

Config file: `configs/{env}/ssm.yaml`

SSM Parameter Store is for **non-sensitive configuration values only**.
For secrets and credentials (passwords, API keys, tokens) use **AWS Secrets Manager**.

Supports two parameter types:

| Type | Notes |
|---|---|
| `String` | Single plain-text configuration value |
| `StringList` | YAML list stored as a comma-separated string in AWS |

#### Schema

```yaml
environment: dev
region: us-east-1

# Non-sensitive configuration values only.
# Secrets and credentials belong in AWS Secrets Manager.

ssm:
  parameters:

    # String
    - name: /myapp/db/host          # required — must start with /
      type: String                  # String | StringList
      value: db.example.com
      description: "Database host"  # optional
      tier: Standard                # Standard (default) | Advanced

    # StringList
    - name: /myapp/db/allowed-envs
      type: StringList
      value:
        - dev
        - staging
        - prod
      description: "Allowed environments"
      tier: Standard
```

#### SSM Parameter field reference

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | Yes | — | Parameter path, must start with `/` |
| `type` | Yes | — | `String` or `StringList` |
| `value` | Yes | — | String for `String`; YAML list for `StringList` |
| `description` | No | `""` | Free-text description shown in AWS console |
| `tier` | No | `Standard` | `Standard` or `Advanced` |

> **Note:** `SecureString` is not supported in this module by design.
> Store all secrets in **AWS Secrets Manager**.

---

### Secrets Manager (credentials & secrets)

Config file: `configs/{env}/secrets_manager.yaml`

AWS Secrets Manager is for **sensitive credentials and secrets only**.
For non-sensitive configuration values use **SSM Parameter Store**.

> **Rule:** No actual secret value should ever be committed to version control.
> Use one of the four strategies below to keep values out of YAML files.

Supports four secret strategies:

| Type | Value in config? | How the value is provided |
|---|---|---|
| `Generated` | Never | AWS auto-generates at deploy time |
| `Reference` | Never | Secret pre-exists in AWS; CDK registers it only |
| `PlainText` | `${VAR}` token | Injected from environment variable at synth time |
| `KeyValue` | `${VAR}` tokens per key | Each value injected from env vars at synth time |

#### Schema

```yaml
environment: dev
region: us-east-1

secrets_manager:
  secrets:

    # Generated — AWS creates a strong random value; no value ever in config.
    - name: /myapp/db/password
      type: Generated
      description: "Auto-generated database password"
      generate:
        length: 32                        # optional, default 32
        exclude_characters: "/@\"' "     # optional — chars to exclude
        exclude_punctuation: false        # optional, default false

    # Reference — secret already exists in AWS; CDK registers reference only.
    - name: /myapp/legacy/api-key
      type: Reference
      description: "Pre-existing secret managed externally"

    # PlainText — set env var before synth: export MY_TOKEN=<value>
    - name: /myapp/api/token
      type: PlainText
      value: ${MY_TOKEN}
      description: "Third-party API token"

    # KeyValue — each value may be a literal or a ${VAR} token.
    - name: /myapp/db/connection
      type: KeyValue
      value:
        username: ${DB_USER}
        dbname: ${DB_NAME}
        host: db.example.com
        port: "5432"
      description: "Database connection details"
```

#### Secrets Manager field reference

| Field | Required for | Description |
|---|---|---|
| `name` | All | Secret name/path, must start with `/` |
| `type` | All | `Generated`, `Reference`, `PlainText`, or `KeyValue` |
| `description` | — | Free-text description shown in AWS console (optional) |
| `value` | `PlainText`, `KeyValue` | String or mapping; use `${VAR}` for env injection |
| `generate` | `Generated` | Sub-block controlling random value generation |
| `generate.length` | — | Password length, minimum 8 (default: 32) |
| `generate.exclude_characters` | — | Characters to exclude from generated value |
| `generate.exclude_punctuation` | — | If true, strips all punctuation (default: false) |

#### Env var injection

`${VAR}` tokens in `PlainText` and `KeyValue` values are resolved from `os.environ`
at CDK synth time. If a referenced variable is not set, synthesis fails immediately
with a clear error — the problem is caught before deployment, not at runtime.

```bash
# Set required env vars before running cdk synth / cdk deploy
export MY_TOKEN=my-real-token
export DB_USER=mydbuser
export DB_NAME=myapp_dev

CDK_ENV=dev cdk deploy --all
```

---

## Usage

All CDK commands are run from the `aws/` directory.

```bash
cd aws

# Synthesise CloudFormation templates (no AWS credentials needed)
CDK_ENV=dev cdk synth

# Show what will change before deploying
CDK_ENV=dev cdk diff

# Deploy to AWS (requires configured AWS credentials)
CDK_ENV=dev cdk deploy --all

# Destroy all stacks
CDK_ENV=dev cdk destroy --all
```

#### AWS credentials

CDK uses the standard AWS credential chain. Configure via:

```bash
# Option 1 — environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

# Option 2 — AWS CLI profile
aws configure --profile myprofile
export AWS_PROFILE=myprofile
```

---

## Extending — Adding a New Service

Adding a new AWS service (e.g. S3) requires **zero changes to the core framework**. Create four files and register in `main.py`:

**1. Config model** — `src/config/models/s3.py`
```python
from config.models.base import BaseConfig
from dataclasses import dataclass, field

@dataclass
class S3Config(BaseConfig):
    buckets: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, environment, region, raw):
        return cls(environment=environment, region=region, buckets=raw.get("buckets", []))
```

**2. CDK Stack** — `src/stacks/s3_stack.py`
```python
from stacks.base import BaseServiceStack

class S3Stack(BaseServiceStack):
    def __init__(self, scope, config, **kwargs):
        super().__init__(scope, "s3", config, **kwargs)

    def _build(self):
        for bucket_config in self._config.buckets:
            S3BucketConstruct(self, bucket_config)
```

**3. CDK Construct** — `src/services/s3/construct.py`
```python
from services.base import BaseServiceConstruct

class S3BucketConstruct(BaseServiceConstruct):
    def _create_resource(self):
        # create aws_s3.Bucket here
```

**4. Config file** — `configs/dev/s3.yaml`
```yaml
environment: dev
region: us-east-1

s3:
  buckets:
    - name: my-app-assets
      versioning: true
```

**5. Register in `src/main.py`**
```python
from config.models.s3 import S3Config
from stacks.s3_stack import S3Stack

s3_config: S3Config = loader.load("s3", ENV)
S3Stack(app, s3_config)
```

---

## Design Principles

| Principle | How it is applied |
|---|---|
| **Abstraction** | `BaseConfigLoader`, `BaseServiceStack`, `BaseServiceConstruct`, `BaseSsmParameter` define contracts — callers never depend on concrete classes |
| **Inheritance** | Every service stack, construct, config, and loader extends a shared abstract base |
| **Encapsulation** | Internal CDK resource creation is `_private` to each class; public surface is minimal |
| **Polymorphism** | SSM type handlers (`String`, `StringList`, `SecureString`) are interchangeable strategies dispatched by a registry |
| **Open/Closed** | New services extend the framework without modifying it |
| **DRY** | Tags, naming conventions, and error handling live once in the base layer |
