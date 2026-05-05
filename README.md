# de-aws-cdk

Config-driven AWS infrastructure mono-repo. Declare AWS resources in YAML files — the framework synthesises and deploys them via AWS CDK (Python) and CloudFormation.

---

## Modules

| Module | Description | Docs |
|---|---|---|
| `aws/` | Config-driven AWS CDK infrastructure (Python) | [README](aws/README.md) |

---

## Repository Structure

```
de-aws-cdk/
├── .venv/                      # Shared Python virtual environment
└── aws/                        # AWS CDK infrastructure module
    ├── cdk.json                # CDK app entry point and feature flags
    ├── requirements.txt        # Python dependencies
    ├── configs/                # YAML resource declarations
    │   └── {env}/
    │       └── {project}/
    │           └── {region}/
    │               ├── ssm.yaml
    │               ├── secrets_manager.yaml
    │               ├── iam.yaml
    │               └── s3.yaml
    ├── src/                    # CDK stacks, constructs, and config models
    └── README.md
```

---

## Quick Start

```bash
# Clone and set up the shared virtual environment
git clone <repo-url>
cd de-aws-cdk
python -m venv .venv
source .venv/bin/activate
pip install -r aws/requirements.txt

# Install the CDK CLI
npm install -g aws-cdk

# Synthesise CloudFormation templates (no AWS credentials needed)
cd aws
CDK_ENV=dev CDK_PROJECT=myapp CDK_REGION=us-east-1 cdk synth
```

See [aws/README.md](aws/README.md) for full usage details, configuration reference, and how to add new services.

---

## Supported AWS Services

| Service | Config file | Purpose |
|---|---|---|
| SSM Parameter Store | `ssm.yaml` | Non-sensitive configuration values (`String`, `StringList`) |
| Secrets Manager | `secrets_manager.yaml` | Credentials and secrets (`Generated`, `Reference`, `PlainText`, `KeyValue`) |
| IAM | `iam.yaml` | Roles, managed policies, users, groups, OIDC providers |
| S3 | `s3.yaml` | Buckets with full lifecycle, encryption, CORS, logging, and website support |
