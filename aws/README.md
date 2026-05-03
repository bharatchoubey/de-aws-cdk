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
    │   ├── secrets_manager_stack.py      # SecretsManagerStack
    │   └── iam_stack.py                  # IamStack
    └── services/
        ├── base.py                       # BaseServiceConstruct (abstract CDK Construct)
        ├── ssm/
        │   ├── construct.py              # SsmParameterConstruct
        │   └── types/
        │       ├── base.py               # BaseSsmParameter (strategy ABC)
        │       ├── string.py             # StringParameter
        │       └── string_list.py        # StringListParameter
        ├── secrets_manager/
        │   ├── env_resolver.py           # ${VAR} token resolver
        │   ├── construct.py              # SecretConstruct
        │   └── types/
        │       ├── base.py               # BaseSecretType (strategy ABC)
        │       ├── plain_text.py         # PlainTextSecret
        │       ├── key_value.py          # KeyValueSecret
        │       ├── generated.py          # GeneratedSecret
        │       └── reference.py          # ReferenceSecret
        └── iam/
            ├── construct_role.py         # IamRoleConstruct
            ├── construct_policy.py       # IamPolicyConstruct
            ├── construct_oidc_provider.py# IamOidcProviderConstruct
            ├── construct_group.py        # IamGroupConstruct
            ├── construct_user.py         # IamUserConstruct
            └── principals/
                ├── base.py               # BasePrincipal (strategy ABC)
                ├── service.py            # ServicePrincipal
                ├── account.py            # AccountPrincipal
                ├── arn.py                # ArnPrincipal
                ├── federated.py          # FederatedPrincipal (OIDC / web identity)
                └── saml.py               # SamlPrincipal (SAML 2.0)
```

---

## Setup

The virtual environment is shared across all modules and lives at the project root.

```bash
# From the project root (de-aws-cdk/)
python -m venv .venv
source .venv/bin/activate

# Install all module dependencies
pip install -r aws/requirements.txt
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

| Service | Config file | Purpose |
|---|---|---|
| SSM Parameter Store | `configs/{env}/ssm.yaml` | Non-sensitive configuration values |
| Secrets Manager | `configs/{env}/secrets_manager.yaml` | Credentials and secrets |
| IAM | `configs/{env}/iam.yaml` | Roles, policies, users, groups, OIDC providers |

---

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

| Field | Applies to | Required | Default | Description |
|---|---|---|---|---|
| `name` | All | Yes | — | Parameter path, must start with `/` |
| `type` | All | Yes | — | `String` or `StringList` |
| `value` | All | Yes | — | String scalar for `String`; YAML list for `StringList` |
| `description` | All | No | `""` | Free-text description shown in AWS console |
| `tier` | All | No | `Standard` | `Standard` or `Advanced` |
| `tags` | All | No | `{}` | Key/value tags applied to the parameter resource |
| `allowed_pattern` | `String` only | No | `""` | Regex the value must match at creation time |
| `data_type` | `String` only | No | `text` | `text` (default) or `aws:ec2:image` — the latter validates that the value is a real AMI ID |

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

| Field | Applies to | Required | Description |
|---|---|---|---|
| `name` | All | Yes | Secret name/path, must start with `/` |
| `type` | All | Yes | `Generated`, `Reference`, `PlainText`, or `KeyValue` |
| `description` | All | No | Free-text description shown in AWS console |
| `value` | `PlainText`, `KeyValue` | Yes | String or mapping; use `${VAR}` for env injection |
| `tags` | All except `Reference` | No | Key/value tags applied to the secret resource |
| `removal_policy` | All except `Reference` | No | `DESTROY` (default), `RETAIN`, or `SNAPSHOT`. Use `RETAIN` for production secrets to prevent accidental deletion. |
| `kms_key_arn` | All except `Reference` | No | ARN of a customer-managed KMS key for at-rest encryption. Omit to use the AWS-managed key. |
| `replica_regions` | All except `Reference` | No | List of AWS regions to replicate the secret into (e.g. `[us-west-2]`) |
| `generate` | `Generated` | Yes | Sub-block controlling random value generation |
| `generate.length` | `Generated` | No | Password length, minimum 8 (default: 32) |
| `generate.exclude_characters` | `Generated` | No | Characters to exclude (e.g. `"/@\"' "` for connection strings) |
| `generate.exclude_punctuation` | `Generated` | No | Strip all punctuation (default: false) |
| `generate.include_space` | `Generated` | No | Allow spaces in the generated value (default: false) |
| `generate.require_each_included_type` | `Generated` | No | Guarantee at least one uppercase, lowercase, digit, and symbol (default: false) |
| `generate.secret_string_template` | `Generated` | No | JSON template for non-generated fields, e.g. `'{"username": "admin"}'`. Must be used with `generate_string_key`. |
| `generate.generate_string_key` | `Generated` | No | JSON key where the generated password is placed. Required when `secret_string_template` is set. Produces RDS/Aurora rotation-compatible secrets. |

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

### IAM

Config file: `configs/{env}/iam.yaml`

Manages all core IAM resource types from a single config file.
All sections are optional — define only the resources your environment needs.

#### Resource types

| Section | AWS Resource | Purpose |
|---|---|---|
| `oidc_providers` | `iam.OpenIdConnectProvider` | GitHub Actions OIDC, EKS IRSA, Cognito federation |
| `groups` | `iam.Group` | Attach permissions to sets of users |
| `users` | `iam.User` | IAM users (no passwords/keys in config) |
| `roles` | `iam.Role` | Service, account, federated, SAML, and composite trust |
| `policies` | `iam.ManagedPolicy` | Standalone reusable permission sets |

#### Principal types (`assumed_by`)

| Type | When to use | `principal` value |
|---|---|---|
| `service` | AWS service assumes the role | `ec2.amazonaws.com`, `lambda.amazonaws.com`, etc. |
| `account` | All identities in an AWS account | AWS account ID string e.g. `"123456789012"` |
| `arn` | Specific IAM user/role ARN | Full ARN |
| `federated` | OIDC / web identity (GitHub Actions, EKS pods) | OIDC provider URL |
| `saml` | SAML 2.0 enterprise SSO (Okta, Azure AD) | SAML provider ARN |

For **composite** trust (multiple principals on one role), supply a YAML list under `assumed_by`.

#### Schema

```yaml
environment: dev
region: us-east-1

iam:

  # ── OIDC Identity Providers ────────────────────────────────────────────
  oidc_providers:
    - name: github-actions-oidc
      url: https://token.actions.githubusercontent.com   # must be HTTPS
      client_ids:
        - sts.amazonaws.com
      thumbprints: []                                    # optional for public providers

  # ── Groups ─────────────────────────────────────────────────────────────
  groups:
    - name: myapp-developers
      path: /myapp/                  # optional, default "/"
      managed_policies:
        - arn:aws:iam::aws:policy/ReadOnlyAccess

  # ── Users ──────────────────────────────────────────────────────────────
  users:
    - name: myapp-svc-account
      path: /myapp/service-accounts/
      groups:                        # must be group names defined above
        - myapp-developers
      managed_policies:
        - arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
      tags:
        team: platform

  # ── Roles ──────────────────────────────────────────────────────────────
  roles:

    # Single service principal
    - name: myapp-lambda-role
      description: "Lambda execution role"
      path: /myapp/
      permission_boundary: arn:aws:iam::aws:policy/PowerUserAccess  # optional
      assumed_by:
        type: service
        principal: lambda.amazonaws.com
      managed_policies:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      inline_policies:
        - name: SsmAccess
          statements:
            - effect: Allow
              sid: ReadParams               # optional
              actions: [ssm:GetParameter]
              resources: [arn:aws:ssm:*:*:parameter/myapp/*]
            - effect: Deny
              not_actions: [ssm:GetParameter]   # inverse — deny everything else
              not_resources: ["*"]
      max_session_duration_hours: 1
      tags:
        team: backend

    # Composite principal — EC2 and Lambda share the same role
    - name: myapp-shared-role
      assumed_by:
        - type: service
          principal: ec2.amazonaws.com
        - type: service
          principal: lambda.amazonaws.com
      managed_policies:
        - arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

    # Federated — GitHub Actions OIDC keyless CI/CD
    - name: myapp-github-deploy-role
      assumed_by:
        type: federated
        principal: token.actions.githubusercontent.com
        conditions:
          StringEquals:
            token.actions.githubusercontent.com:aud: sts.amazonaws.com
          StringLike:
            token.actions.githubusercontent.com:sub: repo:myorg/myrepo:*
      managed_policies:
        - arn:aws:iam::aws:policy/PowerUserAccess

    # SAML — enterprise SSO
    - name: myapp-sso-role
      assumed_by:
        type: saml
        principal: arn:aws:iam::123456789012:saml-provider/MyProvider
        conditions:
          StringEquals:
            SAML:aud: https://signin.aws.amazon.com/saml
      managed_policies:
        - arn:aws:iam::aws:policy/ReadOnlyAccess
      max_session_duration_hours: 8

  # ── Managed Policies ───────────────────────────────────────────────────
  policies:
    - name: myapp-ssm-read-policy
      description: "SSM read access for myapp"
      path: /myapp/
      tags:
        team: platform
      statements:
        - effect: Allow
          actions:
            - ssm:GetParameter
            - ssm:GetParametersByPath
          resources:
            - arn:aws:ssm:*:*:parameter/myapp/*
          conditions:
            StringEquals:
              aws:RequestedRegion: us-east-1
```

#### Field reference

**OIDC Provider**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Logical identifier (becomes construct ID) |
| `url` | Yes | HTTPS OIDC provider URL |
| `client_ids` | Yes | Allowed audiences (usually `sts.amazonaws.com`) |
| `thumbprints` | No | Server certificate thumbprints (auto-fetched for public providers) |

**Group**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | IAM group name |
| `path` | No | IAM path, default `/` |
| `managed_policies` | No | List of managed policy ARNs to attach |

**User**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | IAM user name |
| `path` | No | IAM path, default `/` |
| `groups` | No | Group names (must be defined in the same YAML) |
| `managed_policies` | No | Managed policy ARNs to attach directly |
| `tags` | No | Key/value tags |

> Passwords and access keys are excluded by design. Credentials must never be stored in config files.

**Role**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | IAM role name |
| `assumed_by` | Yes | Single `{type, principal}` dict **or** a list for composite trust |
| `assumed_by[].type` | Yes | `service`, `account`, `arn`, `federated`, or `saml` |
| `assumed_by[].principal` | Yes | Service URL, account ID, ARN, OIDC URL, or SAML ARN |
| `assumed_by[].conditions` | No | Trust policy conditions (for `federated` / `saml`) |
| `description` | No | Free-text description |
| `path` | No | IAM path, default `/` |
| `permission_boundary` | No | Managed policy ARN that caps the role's max permissions |
| `managed_policies` | No | List of managed policy ARNs |
| `inline_policies` | No | Embedded policy documents |
| `max_session_duration_hours` | No | 1–12, default `1` |
| `tags` | No | Key/value tags |

**Managed Policy**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Policy name |
| `statements` | Yes | List of policy statements |
| `description` | No | Free-text description |
| `path` | No | IAM path, default `/` |
| `tags` | No | Key/value tags |

**Policy Statement** (used in inline policies and managed policies)

| Field | Required | Description |
|---|---|---|
| `effect` | Yes | `Allow` or `Deny` |
| `actions` | Yes* | List of IAM actions (`s3:GetObject`, etc.) |
| `resources` | Yes* | List of resource ARNs |
| `not_actions` | No | Inverse action set (use with permission boundaries) |
| `not_resources` | No | Inverse resource set |
| `sid` | No | Statement identifier |
| `conditions` | No | IAM condition key-value map |

\* One of `actions`/`not_actions` and one of `resources`/`not_resources` must be provided.

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
