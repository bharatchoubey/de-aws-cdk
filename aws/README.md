# aws — Config-Driven AWS Infrastructure (CDK)

A config-driven AWS infrastructure module built on **AWS CDK (Python)**. Declare AWS resources in YAML — the framework validates, synthesises, and deploys them via CloudFormation. Adding a new AWS service requires no changes to the core framework.

---

## Table of Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Configuration](#configuration)
  - [Directory layout](#directory-layout)
  - [Environment variables](#environment-variables)
  - [Adding a new environment or project](#adding-a-new-environment-or-project)
- [Supported Services](#supported-services)
  - [SSM Parameter Store](#ssm-parameter-store)
  - [Secrets Manager](#secrets-manager)
  - [IAM](#iam)
  - [S3](#s3)
- [Usage](#usage)
- [Logging](#logging)
- [Naming Conventions](#naming-conventions)
- [Extending — Adding a New Service](#extending--adding-a-new-service)
- [Design Principles](#design-principles)

---

## Architecture

```
YAML Config  →  Config Loader  →  Config Model  →  CDK Stack  →  CDK Construct  →  AWS
```

Each AWS service follows the same layered pattern:

| Layer | Responsibility |
|---|---|
| `configs/{env}/{project}/{region}/{service}.yaml` | Declare what resources to create |
| `config/loader.py` | Parse the YAML, resolve the path, construct typed models |
| `config/models/{service}.py` | Typed, validated dataclass for one service |
| `stacks/{service}_stack.py` | CDK Stack — iterates resources, delegates to constructs |
| `services/{service}/construct.py` | CDK Construct — one logical resource |
| `services/{service}/types/` | Strategy per resource sub-type (where applicable) |

---

## Project Structure

```
aws/
├── cdk.json                          # CDK app entry point and feature flags
├── requirements.txt                  # Python dependencies
├── .run.sh                           # Local dev helper script
├── configs/
│   └── {env}/                        # e.g. dev, staging, prod
│       └── {project}/                # e.g. myapp, payments
│           └── {region}/             # e.g. us-east-1, eu-west-1
│               ├── ssm.yaml
│               ├── secrets_manager.yaml
│               ├── iam.yaml
│               └── s3.yaml
└── src/
    ├── main.py                       # CDK App entry — loads configs, mounts stacks
    ├── logger.py                     # Centralised logger factory
    ├── config/
    │   ├── base.py                   # BaseConfigLoader (abstract)
    │   ├── loader.py                 # YamlConfigLoader
    │   └── models/
    │       ├── base.py               # BaseConfig dataclass (project, environment, region)
    │       ├── ssm.py                # SsmConfig, SsmParameterConfig
    │       ├── secrets_manager.py    # SecretsManagerConfig, SecretConfig
    │       ├── iam.py                # IamConfig and all IAM sub-models
    │       └── s3.py                 # S3Config, S3BucketConfig, lifecycle/CORS/tiering models
    ├── stacks/
    │   ├── base.py                   # BaseServiceStack (abstract CDK Stack)
    │   ├── ssm_stack.py              # SsmStack
    │   ├── secrets_manager_stack.py  # SecretsManagerStack
    │   ├── iam_stack.py              # IamStack
    │   └── s3_stack.py               # S3Stack
    └── services/
        ├── base.py                   # BaseServiceConstruct (abstract CDK Construct)
        ├── ssm/
        │   ├── construct.py          # SsmParameterConstruct
        │   └── types/
        │       ├── base.py           # BaseSsmParameter (strategy ABC)
        │       ├── string.py         # StringParameter
        │       └── string_list.py    # StringListParameter
        ├── secrets_manager/
        │   ├── construct.py          # SecretConstruct
        │   ├── env_resolver.py       # ${VAR} token resolver
        │   └── types/
        │       ├── base.py           # BaseSecretType (strategy ABC)
        │       ├── generated.py      # GeneratedSecret
        │       ├── reference.py      # ReferenceSecret
        │       ├── plain_text.py     # PlainTextSecret
        │       └── key_value.py      # KeyValueSecret
        ├── iam/
        │   ├── construct_role.py         # IamRoleConstruct
        │   ├── construct_policy.py       # IamPolicyConstruct
        │   ├── construct_oidc_provider.py# IamOidcProviderConstruct
        │   ├── construct_group.py        # IamGroupConstruct
        │   ├── construct_user.py         # IamUserConstruct
        │   └── principals/
        │       ├── base.py           # BasePrincipal (strategy ABC)
        │       ├── service.py        # ServicePrincipal
        │       ├── account.py        # AccountPrincipal
        │       ├── arn.py            # ArnPrincipal
        │       ├── federated.py      # FederatedPrincipal (OIDC / web identity)
        │       └── saml.py           # SamlPrincipal (SAML 2.0)
        └── s3/
            └── construct.py          # S3BucketConstruct
```

---

## Setup

The virtual environment is shared across all modules and lives at the project root.

```bash
# From the project root (de-aws-cdk/)
python -m venv .venv
source .venv/bin/activate
pip install -r aws/requirements.txt
```

Install the AWS CDK CLI:

```bash
npm install -g aws-cdk
```

---

## Configuration

### Directory layout

Config files live under a **four-level path hierarchy**:

```
configs/{env}/{project}/{region}/{service}.yaml
```

| Path segment | Env variable | Default | Example |
|---|---|---|---|
| `{env}` | `CDK_ENV` | `dev` | `dev`, `staging`, `prod` |
| `{project}` | `CDK_PROJECT` | `myapp` | `myapp`, `payments`, `data-platform` |
| `{region}` | `CDK_REGION` | `us-east-1` | `us-east-1`, `eu-west-1` |
| `{service}` | (file name) | — | `ssm`, `secrets_manager`, `iam`, `s3` |

Because the directory path already encodes `env`, `project`, and `region`, YAML files contain **only service-specific resource declarations** — no metadata headers.

```yaml
# configs/dev/myapp/us-east-1/ssm.yaml
# Just the parameters — no project/environment/region fields needed.

parameters:
  - name: /myapp/db/host
    type: String
    value: db.dev.example.com
```

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `CDK_ENV` | `dev` | Selects the environment directory |
| `CDK_PROJECT` | `myapp` | Selects the project directory |
| `CDK_REGION` | `us-east-1` | Selects the AWS region directory |
| `LOG_LEVEL` | `INFO` | Logger verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Adding a new environment or project

```bash
# New environment for the same project
mkdir -p configs/prod/myapp/us-east-1
cp configs/dev/myapp/us-east-1/*.yaml configs/prod/myapp/us-east-1/
# Edit the copied files with prod values

CDK_ENV=prod CDK_PROJECT=myapp CDK_REGION=us-east-1 cdk deploy --all

# New project in the same environment
mkdir -p configs/dev/payments/us-east-1
# Create configs/dev/payments/us-east-1/*.yaml

CDK_ENV=dev CDK_PROJECT=payments CDK_REGION=us-east-1 cdk deploy --all

# Deploy to a different region
mkdir -p configs/dev/myapp/eu-west-1
cp configs/dev/myapp/us-east-1/*.yaml configs/dev/myapp/eu-west-1/
# Edit with region-specific values

CDK_ENV=dev CDK_PROJECT=myapp CDK_REGION=eu-west-1 cdk deploy --all
```

---

## Supported Services

### SSM Parameter Store

Config file: `configs/{env}/{project}/{region}/ssm.yaml`

SSM Parameter Store is for **non-sensitive configuration values only**.
For secrets and credentials (passwords, API keys, tokens) use **AWS Secrets Manager**.

> `SecureString` is not supported by design. Store all secrets in **AWS Secrets Manager**.

Supports two parameter types:

| Type | Notes |
|---|---|
| `String` | Single plain-text configuration value |
| `StringList` | YAML list; stored as comma-separated string in AWS |

#### Schema

```yaml
# configs/dev/myapp/us-east-1/ssm.yaml

parameters:

  # String — minimal
  - name: /myapp/db/host          # required, must start with /
    type: String
    value: db.example.com
    description: "Database hostname"  # optional
    tier: Standard                    # Standard (default) | Advanced

  # String with tags and validation
  - name: /myapp/cache/endpoint
    type: String
    value: redis.example.com:6379
    tier: Standard
    allowed_pattern: "^[a-zA-Z0-9._-]+:[0-9]{1,5}$"   # regex validated at deploy time
    data_type: text                                      # text (default) | aws:ec2:image
    tags:
      team: platform

  # StringList — YAML list stored as comma-separated string in AWS
  - name: /myapp/db/allowed-envs
    type: StringList
    value:
      - dev
      - staging
      - prod
    description: "Allowed deployment environments"
    tier: Standard
```

#### Field reference

| Field | Applies to | Required | Default | Description |
|---|---|---|---|---|
| `name` | All | Yes | — | Parameter path, must start with `/` |
| `type` | All | Yes | — | `String` or `StringList` |
| `value` | All | Yes | — | String scalar for `String`; YAML list for `StringList` |
| `description` | All | No | `""` | Free-text description shown in AWS console |
| `tier` | All | No | `Standard` | `Standard` or `Advanced` |
| `tags` | All | No | `{}` | Key/value tags applied to the parameter |
| `allowed_pattern` | `String` | No | `""` | Regex the value must match at creation time |
| `data_type` | `String` | No | `text` | `text` or `aws:ec2:image` (validates the value is a real AMI ID) |

---

### Secrets Manager

Config file: `configs/{env}/{project}/{region}/secrets_manager.yaml`

AWS Secrets Manager is for **sensitive credentials and secrets only**.
For non-sensitive configuration use **SSM Parameter Store**.

> **Rule:** No actual secret value should ever be committed to version control.
> Use one of the four strategies below to keep values out of YAML files.

| Type | Value in config? | How the value is provided |
|---|---|---|
| `Generated` | Never | AWS auto-generates a strong random value at deploy time |
| `Reference` | Never | Secret pre-exists in AWS; CDK registers a reference only |
| `PlainText` | `${VAR}` token | Injected from environment variable at synth time |
| `KeyValue` | `${VAR}` tokens per key | Each value injected from env vars at synth time |

#### Schema

```yaml
# configs/dev/myapp/us-east-1/secrets_manager.yaml

secrets:

  # Generated — AWS creates a strong random value; no value in config.
  - name: /myapp/db/password
    type: Generated
    description: "Auto-generated database password"
    removal_policy: RETAIN
    tags:
      team: platform
    generate:
      length: 32
      exclude_characters: "/@\"' "        # prevent chars that break connection strings

  # Generated with RDS/Aurora rotation-compatible JSON format.
  # Produces: {"username": "admin", "password": "<generated>"}
  - name: /myapp/db/rds-credentials
    type: Generated
    generate:
      length: 32
      secret_string_template: '{"username": "admin"}'
      generate_string_key: "password"

  # Generated — customer KMS key + cross-region replication
  - name: /myapp/auth/session-key
    type: Generated
    kms_key_arn: arn:aws:kms:us-east-1:123456789012:key/mrk-abc123
    replica_regions:
      - us-west-2
    generate:
      length: 64

  # Reference — secret already exists; CDK registers reference only.
  - name: /myapp/legacy/api-key
    type: Reference
    description: "Pre-existing API key managed externally"

  # PlainText — set env var before synth: export MY_TOKEN=<value>
  - name: /myapp/api/token
    type: PlainText
    value: ${MY_TOKEN}
    description: "Third-party API token"
    removal_policy: RETAIN

  # KeyValue — JSON object; each value may be a ${VAR} token.
  # Set before synth: export DB_USER=myuser && export DB_NAME=myapp_dev
  - name: /myapp/db/connection
    type: KeyValue
    value:
      username: ${DB_USER}
      dbname: ${DB_NAME}
      host: db.example.com
      port: "5432"
    removal_policy: RETAIN
```

#### Field reference

| Field | Applies to | Required | Description |
|---|---|---|---|
| `name` | All | Yes | Secret name/path, must start with `/` |
| `type` | All | Yes | `Generated`, `Reference`, `PlainText`, or `KeyValue` |
| `description` | All | No | Free-text description shown in AWS console |
| `value` | `PlainText`, `KeyValue` | Yes | String or mapping; use `${VAR}` for env injection |
| `tags` | All except `Reference` | No | Key/value tags |
| `removal_policy` | All except `Reference` | No | `DESTROY` (default) \| `RETAIN` \| `SNAPSHOT`. Use `RETAIN` for production. |
| `kms_key_arn` | All except `Reference` | No | Customer-managed KMS key ARN for at-rest encryption |
| `replica_regions` | All except `Reference` | No | List of AWS regions to replicate the secret into |
| `generate` | `Generated` | Yes | Sub-block controlling random value generation |
| `generate.length` | `Generated` | No | Password length, minimum 8 (default: 32) |
| `generate.exclude_characters` | `Generated` | No | Characters to exclude (e.g. `"/@\"' "`) |
| `generate.exclude_punctuation` | `Generated` | No | Strip all punctuation (default: false) |
| `generate.include_space` | `Generated` | No | Allow spaces (default: false) |
| `generate.require_each_included_type` | `Generated` | No | Require uppercase + lowercase + digit + symbol (default: false) |
| `generate.secret_string_template` | `Generated` | No | JSON template for non-generated fields (e.g. `'{"username": "admin"}'`) |
| `generate.generate_string_key` | `Generated` | No | JSON key where the generated password is placed. Required when `secret_string_template` is set. |

#### Env-var injection (`${VAR}`)

`${VAR}` tokens in `PlainText` and `KeyValue` values are resolved from `os.environ` at CDK synth time. If a referenced variable is not set, synthesis fails immediately with a clear error — the problem is caught before deployment, not at runtime.

```bash
export THIRD_PARTY_TOKEN=my-real-token
export DB_USER=mydbuser
export DB_NAME=myapp_dev

CDK_ENV=dev CDK_PROJECT=myapp CDK_REGION=us-east-1 cdk deploy --all
```

---

### IAM

Config file: `configs/{env}/{project}/{region}/iam.yaml`

Manages all core IAM resource types from a single file.
All sections are optional — define only the resources your environment needs.

| Section | AWS Resource | Purpose |
|---|---|---|
| `oidc_providers` | `iam.OpenIdConnectProvider` | GitHub Actions OIDC, EKS IRSA, Cognito federation |
| `groups` | `iam.Group` | Attach permissions to sets of users |
| `users` | `iam.User` | IAM users (no passwords or access keys in config) |
| `roles` | `iam.Role` | Service, account, federated, SAML, and composite trust |
| `policies` | `iam.ManagedPolicy` | Standalone reusable permission sets |

#### Principal types (`assumed_by`)

| Type | When to use | `principal` value |
|---|---|---|
| `service` | AWS service assumes the role | `ec2.amazonaws.com`, `lambda.amazonaws.com`, etc. |
| `account` | All identities in an AWS account | AWS account ID string, e.g. `"123456789012"` |
| `arn` | Specific IAM user or role | Full ARN |
| `federated` | OIDC / web identity (GitHub Actions, EKS pods) | OIDC provider URL |
| `saml` | SAML 2.0 enterprise SSO (Okta, Azure AD) | SAML provider ARN |

For **composite** trust (multiple principals on one role), supply a YAML list under `assumed_by`.

#### Schema

```yaml
# configs/dev/myapp/us-east-1/iam.yaml

# ── OIDC Identity Providers ────────────────────────────────────────────
oidc_providers:
  - name: github-actions-oidc
    url: https://token.actions.githubusercontent.com
    client_ids:
      - sts.amazonaws.com
    thumbprints: []                       # optional for well-known public providers

# ── Groups ─────────────────────────────────────────────────────────────
groups:
  - name: myapp-developers
    path: /myapp/                         # optional, default "/"
    managed_policies:
      - arn:aws:iam::aws:policy/ReadOnlyAccess

# ── Users ──────────────────────────────────────────────────────────────
users:
  - name: myapp-svc-account
    path: /myapp/service-accounts/
    groups:
      - myapp-developers                  # must be defined in the groups section above
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
    permission_boundary: arn:aws:iam::aws:policy/PowerUserAccess   # optional
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

  # SAML — enterprise SSO (Okta, Azure AD)
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
```

#### Field reference

**OIDC Provider**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Logical identifier (becomes construct ID) |
| `url` | Yes | HTTPS OIDC provider URL |
| `client_ids` | Yes | Allowed audiences (usually `sts.amazonaws.com`) |
| `thumbprints` | No | Server certificate thumbprints (auto-fetched for well-known providers) |

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
| `groups` | No | Group names (must be defined in the same file) |
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
| `assumed_by[].conditions` | No | Trust policy conditions (for `federated`/`saml`) |
| `description` | No | Free-text description |
| `path` | No | IAM path, default `/` |
| `permission_boundary` | No | Managed policy ARN that caps the role's maximum permissions |
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

**Policy Statement** (used in both `inline_policies` and `policies`)

| Field | Required | Description |
|---|---|---|
| `effect` | Yes | `Allow` or `Deny` |
| `actions` | Yes* | List of IAM actions (`s3:GetObject`, etc.) |
| `resources` | Yes* | List of resource ARNs |
| `not_actions` | No | Inverse action set (used with permission boundaries) |
| `not_resources` | No | Inverse resource set |
| `sid` | No | Statement identifier |
| `conditions` | No | IAM condition key-value map |

\* One of `actions`/`not_actions` and one of `resources`/`not_resources` must be provided.

---

### S3

Config file: `configs/{env}/{project}/{region}/s3.yaml`

Manages S3 buckets using the CDK L2 `aws_s3.Bucket` construct. All CDK-supported bucket features are available through config, including encryption, versioning, lifecycle rules, CORS, intelligent tiering, server access logging, and static website hosting.

#### Encryption modes (`encryption`)

| Value | Description |
|---|---|
| `S3_MANAGED` | SSE-S3 (AES-256, AWS-managed key) — recommended default |
| `KMS_MANAGED` | SSE-KMS with AWS-managed key (auditable in CloudTrail) |
| `KMS` | SSE-KMS with customer-managed key (requires `encryption_key_arn`) |
| `DSSE_MANAGED` | Dual-layer SSE-KMS, AWS-managed key |
| `DSSE` | Dual-layer SSE-KMS, customer-managed key (requires `encryption_key_arn`) |
| `UNENCRYPTED` | No server-side encryption (not recommended) |

#### Block public access (`block_public_access`)

| Value | Description |
|---|---|
| `BLOCK_ALL` | All four public-access settings enabled — recommended default |
| `BLOCK_ACLS` | Only ACL-based public access blocked |
| `NONE` | No block — required for public-facing and static-website buckets |

#### Object ownership (`object_ownership`)

| Value | Description |
|---|---|
| `BUCKET_OWNER_ENFORCED` | ACLs disabled; bucket owner owns all objects — recommended |
| `BUCKET_OWNER_PREFERRED` | Bucket owner owns new objects if ACL grants ownership |
| `OBJECT_WRITER` | Object uploader owns the object — required when `public_read_access: true` |

#### Removal policy (`removal_policy`)

| Value | Description |
|---|---|
| `RETAIN` | Keep bucket after stack deletion — recommended for production |
| `DESTROY` | Delete bucket when stack is destroyed (use `auto_delete_objects: true` for non-empty buckets) |

#### Lifecycle transition storage classes

| Value | Minimum age | Notes |
|---|---|---|
| `STANDARD_IA` | 30 days | Infrequent access |
| `ONEZONE_IA` | 30 days | Lower cost, single AZ |
| `INTELLIGENT_TIERING` | None | Automatic tiering |
| `GLACIER_INSTANT_RETRIEVAL` | 90 days | Millisecond retrieval |
| `GLACIER` | 90 days | Minutes-to-hours retrieval |
| `DEEP_ARCHIVE` | 180 days | Cheapest; 12-hour retrieval |

#### Schema

```yaml
# configs/dev/myapp/us-east-1/s3.yaml

buckets:

  # ── Standard application data bucket ─────────────────────────────────
  - name: myapp-data                       # logical name (used for in-stack cross-references)
    bucket_name: myapp-data-dev            # optional physical name; omit for CloudFormation-generated name
    description: "Primary application data bucket"
    versioned: true
    encryption: S3_MANAGED
    block_public_access: BLOCK_ALL
    object_ownership: BUCKET_OWNER_ENFORCED
    removal_policy: RETAIN
    event_bridge_enabled: true             # emit all S3 events to EventBridge
    tags:
      team: platform

  # ── Lifecycle rules ───────────────────────────────────────────────────
  - name: myapp-logs
    encryption: S3_MANAGED
    block_public_access: BLOCK_ALL
    removal_policy: RETAIN
    lifecycle_rules:
      - id: log-tiering
        enabled: true
        prefix: "app-logs/"
        transitions:
          - storage_class: STANDARD_IA
            transition_after: 30          # days
          - storage_class: GLACIER
            transition_after: 90
        expiration: 365                   # expire objects after 365 days
      - id: cleanup-multipart
        enabled: true
        abort_incomplete_multipart_upload_after: 7

  # ── Customer KMS encryption ───────────────────────────────────────────
  - name: myapp-sensitive
    encryption: KMS
    encryption_key_arn: arn:aws:kms:us-east-1:123456789012:key/mrk-abc123
    bucket_key_enabled: true              # reduce KMS API call costs

  # ── Static website hosting ────────────────────────────────────────────
  - name: myapp-website
    encryption: S3_MANAGED
    block_public_access: NONE             # required for public website
    public_read_access: true
    object_ownership: OBJECT_WRITER       # required when public_read_access is true
    website_index_document: index.html
    website_error_document: error.html
    removal_policy: DESTROY
    auto_delete_objects: true             # empty the bucket before deleting

  # ── CORS for browser uploads ──────────────────────────────────────────
  - name: myapp-uploads
    versioned: true
    encryption: S3_MANAGED
    block_public_access: BLOCK_ALL
    cors_rules:
      - id: browser-uploads
        allowed_methods: [PUT, POST, GET]
        allowed_origins:
          - https://app.example.com
        allowed_headers: ["*"]
        exposed_headers: [ETag]
        max_age: 3000

  # ── Intelligent Tiering ───────────────────────────────────────────────
  - name: myapp-ml-datasets
    encryption: KMS_MANAGED
    bucket_key_enabled: true
    transfer_acceleration: true
    intelligent_tiering:
      - name: archive-cold-datasets
        prefix: datasets/
        archive_access_tier_time: 90      # days without access before Archive tier
        deep_archive_access_tier_time: 180
        tags:
          data-type: training-dataset

  # ── Centralized access log target ────────────────────────────────────
  # Create this bucket before buckets that reference it, or list it first.
  - name: myapp-access-logs
    block_public_access: BLOCK_ALL
    object_ownership: BUCKET_OWNER_PREFERRED   # required for log delivery
    removal_policy: RETAIN
    lifecycle_rules:
      - id: expire-access-logs
        enabled: true
        expiration: 90

  # ── Bucket with server access logging enabled ─────────────────────────
  - name: myapp-audited-data
    versioned: true
    encryption: S3_MANAGED
    block_public_access: BLOCK_ALL
    removal_policy: RETAIN
    server_access_logs_bucket: myapp-access-logs  # logical name of a bucket defined above
    server_access_logs_prefix: audited-data/
```

> **In-stack logging:** When `server_access_logs_bucket` references another bucket defined in the
> same config file, the stack automatically adds the required S3 log-delivery bucket policy.
> CDK cannot add that policy to an externally imported bucket — if you reference a bucket
> from another stack by physical name, add the log-delivery policy manually.

#### Bucket field reference

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | Yes | — | Logical name — used for in-stack cross-references (e.g. `server_access_logs_bucket`) |
| `bucket_name` | No | CloudFormation-generated | Physical S3 bucket name |
| `description` | No | `""` | Free-text description (tag only, not a CloudFormation property) |
| `versioned` | No | `false` | Enable S3 object versioning |
| `encryption` | No | `S3_MANAGED` | See [encryption modes](#encryption-modes-encryption) |
| `encryption_key_arn` | No | — | Customer KMS key ARN (`KMS` and `DSSE` modes only) |
| `bucket_key_enabled` | No | `false` | Reduce KMS API call costs (recommended with `KMS`/`KMS_MANAGED`) |
| `block_public_access` | No | `BLOCK_ALL` | See [block public access](#block-public-access-block_public_access) |
| `public_read_access` | No | `false` | Allow unauthenticated GET requests (requires `block_public_access: NONE`) |
| `object_ownership` | No | `BUCKET_OWNER_ENFORCED` | See [object ownership](#object-ownership-object_ownership) |
| `removal_policy` | No | `RETAIN` | See [removal policy](#removal-policy-removal_policy) |
| `auto_delete_objects` | No | `false` | Empty the bucket before destroying it (requires `removal_policy: DESTROY`) |
| `event_bridge_enabled` | No | `false` | Emit all S3 events to Amazon EventBridge |
| `transfer_acceleration` | No | `false` | Enable S3 Transfer Acceleration for faster cross-region uploads |
| `website_index_document` | No | — | Enable static website hosting; value is the index document (e.g. `index.html`) |
| `website_error_document` | No | — | Custom error page for website hosting (e.g. `error.html`) |
| `server_access_logs_bucket` | No | — | Logical or physical name of the target bucket for server access logs |
| `server_access_logs_prefix` | No | `""` | Key prefix for access log objects |
| `lifecycle_rules` | No | `[]` | List of lifecycle rules (see below) |
| `cors_rules` | No | `[]` | List of CORS rules (see below) |
| `intelligent_tiering` | No | `[]` | List of Intelligent-Tiering configurations (see below) |
| `tags` | No | `{}` | Key/value tags applied to the bucket |

**Lifecycle rule fields**

| Field | Required | Description |
|---|---|---|
| `id` | Yes | Unique rule identifier |
| `enabled` | No (default `true`) | Enable or disable the rule |
| `prefix` | No | Object key prefix the rule applies to |
| `expiration` | No | Days after creation to delete objects |
| `transitions` | No | List of `{storage_class, transition_after}` transitions |
| `noncurrent_version_expiration` | No | Days after a version becomes non-current to delete it (versioned buckets) |
| `noncurrent_version_transitions` | No | List of `{storage_class, transition_after}` for non-current versions |
| `abort_incomplete_multipart_upload_after` | No | Days after which to abort incomplete multipart uploads |

**CORS rule fields**

| Field | Required | Description |
|---|---|---|
| `allowed_methods` | Yes | HTTP methods: `GET`, `PUT`, `POST`, `DELETE`, `HEAD` |
| `allowed_origins` | Yes | Allowed origins (e.g. `https://app.example.com`, `"*"`) |
| `allowed_headers` | No | Allowed request headers (e.g. `["*"]`) |
| `exposed_headers` | No | Response headers exposed to the browser (e.g. `[ETag]`) |
| `max_age` | No | Seconds the browser may cache the preflight response |
| `id` | No | Rule identifier |

**Intelligent-Tiering configuration fields**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Configuration identifier |
| `prefix` | No | Object key prefix |
| `archive_access_tier_time` | No | Days of no access before moving to Archive tier (min 90) |
| `deep_archive_access_tier_time` | No | Days of no access before moving to Deep Archive tier (min 180) |
| `tags` | No | Object tags that must match for the rule to apply |

---

## Usage

All CDK commands are run from the `aws/` directory.

```bash
cd aws

# Synthesise CloudFormation templates (no AWS credentials needed)
CDK_ENV=dev CDK_PROJECT=myapp CDK_REGION=us-east-1 cdk synth

# Show what will change before deploying
CDK_ENV=dev CDK_PROJECT=myapp CDK_REGION=us-east-1 cdk diff

# Deploy to AWS (requires configured AWS credentials)
CDK_ENV=dev CDK_PROJECT=myapp CDK_REGION=us-east-1 cdk deploy --all

# Deploy a single stack
CDK_ENV=dev CDK_PROJECT=myapp CDK_REGION=us-east-1 cdk deploy myapp-dev-s3-stack

# Destroy all stacks
CDK_ENV=dev CDK_PROJECT=myapp CDK_REGION=us-east-1 cdk destroy --all
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

#### Helper script

`.run.sh` provides a quick local-dev shortcut with required env vars pre-set:

```bash
bash .run.sh
```

---

## Logging

All synthesis activity is written to `stderr` using Python's standard `logging` module.

```
2026-05-04T00:10:01 [INFO    ] __main__: Starting CDK synthesis (CDK_ENV=dev CDK_PROJECT=myapp CDK_REGION=us-east-1)
2026-05-04T00:10:01 [INFO    ] config.loader: Loading config: service=ssm env=dev project=myapp region=us-east-1 path=...
2026-05-04T00:10:01 [INFO    ] stacks.base: Initializing stack: id=myapp-dev-ssm-stack project=myapp service=ssm region=us-east-1
```

Control verbosity with the `LOG_LEVEL` environment variable:

```bash
LOG_LEVEL=DEBUG CDK_ENV=dev CDK_PROJECT=myapp CDK_REGION=us-east-1 cdk synth
```

| Level | What is shown |
|---|---|
| `DEBUG` | Per-construct creation details, YAML file reads, resolved references |
| `INFO` | Stack initialisation, config loading, stack build summaries (default) |
| `WARNING` | Non-fatal issues (e.g. accessing external log-target bucket by name) |
| `ERROR` | Construction and synthesis failures with context |

---

## Naming Conventions

All CDK stack IDs and construct IDs embed the project name to prevent conflicts when multiple projects share the same CDK module.

| Resource | Pattern | Example |
|---|---|---|
| Stack ID | `{project}-{env}-{service}-stack` | `myapp-dev-s3-stack` |
| Construct ID | `{project}-{construct-name}` | `myapp-myapp-data` |
| Tags (all stacks) | `project`, `environment`, `managed-by`, `service` | — |

The `project` value comes from the `CDK_PROJECT` environment variable and the directory path — it is never hard-coded in YAML.

---

## Extending — Adding a New Service

Adding a new AWS service requires **zero changes to the core framework**. Create four files and register them in `main.py`.

**1. Config model** — `src/config/models/sqs.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from config.models.base import BaseConfig

@dataclass
class SqsQueueConfig:
    name: str
    fifo: bool = False
    visibility_timeout: int = 30

@dataclass
class SqsConfig(BaseConfig):
    queues: list[SqsQueueConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, project: str, environment: str, region: str, raw: dict) -> "SqsConfig":
        queues = [
            SqsQueueConfig(
                name=q["name"],
                fifo=q.get("fifo", False),
                visibility_timeout=q.get("visibility_timeout", 30),
            )
            for q in raw.get("queues", [])
        ]
        return cls(project=project, environment=environment, region=region, queues=queues)
```

**2. CDK Stack** — `src/stacks/sqs_stack.py`

```python
from __future__ import annotations
from constructs import Construct
from config.models.sqs import SqsConfig
from services.sqs.construct import SqsQueueConstruct
from stacks.base import BaseServiceStack

class SqsStack(BaseServiceStack):
    def __init__(self, scope: Construct, config: SqsConfig, **kwargs) -> None:
        super().__init__(scope, "sqs", config, **kwargs)

    def _build(self) -> None:
        for queue_config in self._config.queues:
            SqsQueueConstruct(self, queue_config, name_prefix=self._config.project)
```

**3. CDK Construct** — `src/services/sqs/construct.py`

```python
from __future__ import annotations
import aws_cdk.aws_sqs as sqs
from constructs import Construct
from config.models.sqs import SqsQueueConfig
from services.base import BaseServiceConstruct

class SqsQueueConstruct(BaseServiceConstruct):
    def __init__(self, scope: Construct, config: SqsQueueConfig, name_prefix: str = "") -> None:
        cid = f"{name_prefix}-{config.name}" if name_prefix else config.name
        super().__init__(scope, cid, config)

    def _create_resource(self) -> None:
        config: SqsQueueConfig = self._config
        self.queue = sqs.Queue(
            self,
            "Queue",
            queue_name=config.name,
            fifo=config.fifo,
            visibility_timeout=cdk.Duration.seconds(config.visibility_timeout),
        )
```

**4. Config file** — `configs/dev/myapp/us-east-1/sqs.yaml`

```yaml
# configs/dev/myapp/us-east-1/sqs.yaml

queues:
  - name: myapp-jobs
    fifo: false
    visibility_timeout: 60

  - name: myapp-events.fifo
    fifo: true
    visibility_timeout: 30
```

**5. Register factory and mount in `src/config/loader.py` and `src/main.py`**

In `loader.py`, add to `_SERVICE_FACTORIES`:
```python
"sqs": SqsConfig.from_dict,
```

In `main.py`:
```python
from config.models.sqs import SqsConfig
from stacks.sqs_stack import SqsStack

sqs_config: SqsConfig = loader.load("sqs", ENV, PROJECT, REGION)
SqsStack(app, sqs_config)
```

---

## Design Principles

| Principle | How it is applied |
|---|---|
| **Abstraction** | `BaseConfigLoader`, `BaseServiceStack`, `BaseServiceConstruct` define contracts — callers depend only on interfaces, never concrete classes |
| **Inheritance** | Every stack, construct, config model, and loader extends a shared abstract base |
| **Encapsulation** | Internal CDK resource creation is `_private`; the public surface of each class is minimal |
| **Polymorphism** | SSM type handlers (`String`, `StringList`), Secrets Manager strategies (`Generated`, `Reference`, `PlainText`, `KeyValue`), and IAM principal builders are interchangeable strategies dispatched by type registries |
| **Open/Closed** | New services extend the framework (new files) without modifying any existing core file |
| **Single Responsibility** | Config path resolution, YAML parsing, model validation, CDK synthesis, and resource creation each live in their own class |
| **DRY** | Tags, stack naming, construct ID prefixing, and error handling live once in the base layer and are inherited everywhere |
| **Fail-fast** | Config validation and env-var resolution happen at synth time — errors are caught before any AWS API call is made |
