from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from config.models.base import BaseConfig

VALID_EFFECTS = {"Allow", "Deny"}

# service   — AWS service principal (ec2.amazonaws.com, lambda.amazonaws.com …)
# account   — all identities in an AWS account
# arn       — specific IAM user/role ARN
# federated — OIDC / web identity provider (Cognito, GitHub Actions …)
# saml      — SAML 2.0 identity provider
VALID_PRINCIPAL_TYPES = {"service", "account", "arn", "federated", "saml"}


# ── Policy statement ──────────────────────────────────────────────────────────

@dataclass
class PolicyStatementConfig:
    """
    A single IAM policy statement — the atomic unit of IAM permissions.

    Supports Allow/Deny effects, actions, resources, and optional conditions.
    ``not_actions`` and ``not_resources`` enable inverse permission patterns
    used in permission boundaries.
    """

    effect: str
    actions: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    not_actions: list[str] = field(default_factory=list)
    not_resources: list[str] = field(default_factory=list)
    sid: str = ""
    conditions: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.effect not in VALID_EFFECTS:
            raise ValueError(
                f"Statement 'effect' must be one of {VALID_EFFECTS}. Got: '{self.effect}'"
            )
        if not self.actions and not self.not_actions:
            raise ValueError("Statement must define either 'actions' or 'not_actions'.")
        if not self.resources and not self.not_resources:
            raise ValueError("Statement must define either 'resources' or 'not_resources'.")


# ── Inline policy ─────────────────────────────────────────────────────────────

@dataclass
class InlinePolicyConfig:
    """
    An inline policy embedded directly inside an IAM Role.

    Inline policies are role-specific and do not exist independently.
    Prefer managed policies for reusable permission sets.
    """

    name: str
    statements: list[PolicyStatementConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Inline policy 'name' must be a non-empty string.")
        if not self.statements:
            raise ValueError(f"Inline policy '{self.name}' must have at least one statement.")


# ── Principal (trust policy) ──────────────────────────────────────────────────

@dataclass
class AssumedByConfig:
    """
    Defines a single principal in a role's trust policy.

    Supported types:
      service   — AWS service (e.g. lambda.amazonaws.com)
      account   — AWS account ID ("123456789012")
      arn       — specific IAM ARN
      federated — OIDC provider URL (e.g. token.actions.githubusercontent.com)
      saml      — SAML provider ARN

    For federated and SAML types, use ``conditions`` to restrict the trust
    (e.g. audience check for GitHub Actions OIDC).
    For multiple principals on one role, list them under ``assumed_by``
    in the YAML — they are combined as a CompositePrincipal.
    """

    type: str
    principal: str
    conditions: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.type not in VALID_PRINCIPAL_TYPES:
            raise ValueError(
                f"AssumedBy 'type' must be one of {VALID_PRINCIPAL_TYPES}. Got: '{self.type}'"
            )
        if not self.principal:
            raise ValueError("AssumedBy 'principal' must be a non-empty string.")


# ── IAM Role ──────────────────────────────────────────────────────────────────

@dataclass
class IamRoleConfig:
    """
    Configuration for a single IAM Role.

    ``assumed_by`` accepts a list so that multiple principals can share one
    role (CompositePrincipal). A single-principal role can also use a plain
    dict in YAML — the parser normalises it to a list automatically.
    """

    name: str
    assumed_by: list[AssumedByConfig]
    description: str = ""
    path: str = "/"
    permission_boundary: str = ""
    tags: dict[str, str] = field(default_factory=dict)
    managed_policies: list[str] = field(default_factory=list)
    inline_policies: list[InlinePolicyConfig] = field(default_factory=list)
    max_session_duration_hours: int = 1

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("IAM role 'name' must be a non-empty string.")
        if not self.assumed_by:
            raise ValueError(f"IAM role '{self.name}' must have at least one 'assumed_by' entry.")
        if not (1 <= self.max_session_duration_hours <= 12):
            raise ValueError(
                f"IAM role 'max_session_duration_hours' must be 1–12. "
                f"Got: {self.max_session_duration_hours}"
            )
        for principal in self.assumed_by:
            principal.validate()
        for policy in self.inline_policies:
            policy.validate()

    @property
    def construct_id(self) -> str:
        return self.name.replace("/", "-")


# ── IAM Managed Policy ────────────────────────────────────────────────────────

@dataclass
class IamPolicyConfig:
    """
    Configuration for a standalone AWS Managed Policy.

    Managed policies exist independently and can be attached to multiple
    roles, users, or groups.
    """

    name: str
    statements: list[PolicyStatementConfig]
    description: str = ""
    path: str = "/"
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("IAM policy 'name' must be a non-empty string.")
        if not self.statements:
            raise ValueError(f"IAM policy '{self.name}' must have at least one statement.")
        for stmt in self.statements:
            stmt.validate()

    @property
    def construct_id(self) -> str:
        return self.name.replace("/", "-")


# ── OIDC Identity Provider ────────────────────────────────────────────────────

@dataclass
class OidcProviderConfig:
    """
    Configuration for an IAM OpenID Connect (OIDC) Identity Provider.

    Required for EKS IRSA (pod-level IAM roles), GitHub Actions OIDC,
    and other workload identity federation scenarios.
    """

    name: str
    url: str
    client_ids: list[str]
    thumbprints: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("OIDC provider 'name' must be a non-empty string.")
        if not self.url or not self.url.startswith("https://"):
            raise ValueError(
                f"OIDC provider 'url' must be a valid HTTPS URL. Got: '{self.url}'"
            )
        if not self.client_ids:
            raise ValueError(f"OIDC provider '{self.name}' must have at least one 'client_ids' entry.")

    @property
    def construct_id(self) -> str:
        return self.name.replace("/", "-")


# ── IAM Group ─────────────────────────────────────────────────────────────────

@dataclass
class IamGroupConfig:
    """
    Configuration for an IAM Group.

    Groups provide a way to attach permissions to multiple users at once.
    Users reference their groups by name under ``IamUserConfig.groups``.
    """

    name: str
    path: str = "/"
    managed_policies: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("IAM group 'name' must be a non-empty string.")

    @property
    def construct_id(self) -> str:
        return self.name.replace("/", "-")


# ── IAM User ──────────────────────────────────────────────────────────────────

@dataclass
class IamUserConfig:
    """
    Configuration for an IAM User.

    Login profiles (passwords) and access keys are intentionally excluded —
    credentials must not be stored in config files.

    Users can be assigned to groups defined in the same YAML file by name.
    They can also have managed policies attached directly.
    """

    name: str
    path: str = "/"
    groups: list[str] = field(default_factory=list)
    managed_policies: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("IAM user 'name' must be a non-empty string.")

    @property
    def construct_id(self) -> str:
        return self.name.replace("/", "-")


# ── Top-level IAM config ──────────────────────────────────────────────────────

@dataclass
class IamConfig(BaseConfig):
    """
    Top-level config for the IAM stack.

    All sections are optional — define only what your environment needs.
    Groups are created before users so group references resolve correctly.
    """

    roles: list[IamRoleConfig] = field(default_factory=list)
    policies: list[IamPolicyConfig] = field(default_factory=list)
    oidc_providers: list[OidcProviderConfig] = field(default_factory=list)
    groups: list[IamGroupConfig] = field(default_factory=list)
    users: list[IamUserConfig] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        has_resources = any([
            self.roles, self.policies, self.oidc_providers, self.groups, self.users
        ])
        if not has_resources:
            raise ValueError("'iam' config must define at least one resource.")
        for r in self.roles:
            r.validate()
        for p in self.policies:
            p.validate()
        for o in self.oidc_providers:
            o.validate()
        for g in self.groups:
            g.validate()
        for u in self.users:
            u.validate()
        self._validate_user_groups()

    def _validate_user_groups(self) -> None:
        defined_groups = {g.name for g in self.groups}
        for user in self.users:
            unknown = set(user.groups) - defined_groups
            if unknown:
                raise ValueError(
                    f"User '{user.name}' references undefined groups: {unknown}. "
                    f"Defined groups: {defined_groups or 'none'}"
                )

    @classmethod
    def from_dict(cls, project: str, environment: str, region: str, raw: dict) -> "IamConfig":
        return cls(
            project=project,
            environment=environment,
            region=region,
            roles=[cls._parse_role(r) for r in raw.get("roles", [])],
            policies=[cls._parse_policy(p) for p in raw.get("policies", [])],
            oidc_providers=[cls._parse_oidc(o) for o in raw.get("oidc_providers", [])],
            groups=[cls._parse_group(g) for g in raw.get("groups", [])],
            users=[cls._parse_user(u) for u in raw.get("users", [])],
        )

    @staticmethod
    def _parse_statement(raw: dict) -> PolicyStatementConfig:
        return PolicyStatementConfig(
            effect=raw["effect"],
            actions=raw.get("actions", []),
            resources=raw.get("resources", []),
            not_actions=raw.get("not_actions", []),
            not_resources=raw.get("not_resources", []),
            sid=raw.get("sid", ""),
            conditions=raw.get("conditions", {}),
        )

    @classmethod
    def _parse_inline_policy(cls, raw: dict) -> InlinePolicyConfig:
        return InlinePolicyConfig(
            name=raw["name"],
            statements=[cls._parse_statement(s) for s in raw.get("statements", [])],
        )

    @staticmethod
    def _parse_assumed_by(raw) -> list[AssumedByConfig]:
        """Normalises a single dict or a list of dicts into a list of AssumedByConfig."""
        entries = raw if isinstance(raw, list) else [raw]
        return [
            AssumedByConfig(
                type=e["type"],
                principal=e["principal"],
                conditions=e.get("conditions", {}),
            )
            for e in entries
        ]

    @classmethod
    def _parse_role(cls, raw: dict) -> IamRoleConfig:
        return IamRoleConfig(
            name=raw["name"],
            description=raw.get("description", ""),
            path=raw.get("path", "/"),
            permission_boundary=raw.get("permission_boundary", ""),
            tags=raw.get("tags", {}),
            assumed_by=cls._parse_assumed_by(raw["assumed_by"]),
            managed_policies=raw.get("managed_policies", []),
            inline_policies=[
                cls._parse_inline_policy(ip) for ip in raw.get("inline_policies", [])
            ],
            max_session_duration_hours=raw.get("max_session_duration_hours", 1),
        )

    @classmethod
    def _parse_policy(cls, raw: dict) -> IamPolicyConfig:
        return IamPolicyConfig(
            name=raw["name"],
            description=raw.get("description", ""),
            path=raw.get("path", "/"),
            tags=raw.get("tags", {}),
            statements=[cls._parse_statement(s) for s in raw.get("statements", [])],
        )

    @staticmethod
    def _parse_oidc(raw: dict) -> OidcProviderConfig:
        return OidcProviderConfig(
            name=raw["name"],
            url=raw["url"],
            client_ids=raw["client_ids"],
            thumbprints=raw.get("thumbprints", []),
        )

    @staticmethod
    def _parse_group(raw: dict) -> IamGroupConfig:
        return IamGroupConfig(
            name=raw["name"],
            path=raw.get("path", "/"),
            managed_policies=raw.get("managed_policies", []),
        )

    @staticmethod
    def _parse_user(raw: dict) -> IamUserConfig:
        return IamUserConfig(
            name=raw["name"],
            path=raw.get("path", "/"),
            groups=raw.get("groups", []),
            managed_policies=raw.get("managed_policies", []),
            tags=raw.get("tags", {}),
        )
