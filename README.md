# de-aws-cdk

Config-driven AWS infrastructure mono-repo. Define AWS resources in YAML — the framework synthesises and deploys them via AWS CDK.

---

## Modules

| Module | Description | Docs |
|---|---|---|
| `aws/` | Config-driven AWS CDK infrastructure (Python) | [README](aws/README.md) |
| `cas/` | Config as a Service — Flask REST API for managing application configuration | [README](cas/README.md) |

---

## Repository Structure

```
de-aws-cdk/
├── .venv/              # Shared virtual environment (all modules)
├── aws/                # AWS CDK infrastructure module
│   ├── configs/        # YAML configs per environment
│   ├── src/            # CDK stacks, constructs, config models
│   └── README.md
└── cas/                # Config as a Service (Flask API)
    ├── src/            # Application source
    └── README.md
```

---

## Quick Start

```bash
# Clone and set up shared virtual environment
git clone <repo-url>
cd de-aws-cdk
python -m venv .venv
source .venv/bin/activate
pip install -r aws/requirements.txt -r cas/requirements.txt
```

See each module's README for usage details.

---

## AWS Services Supported

| Service | Purpose |
|---|---|
| SSM Parameter Store | Non-sensitive configuration values |
| Secrets Manager | Credentials and secrets (Generated, Reference, PlainText, KeyValue) |
| IAM | Roles and managed policies |
