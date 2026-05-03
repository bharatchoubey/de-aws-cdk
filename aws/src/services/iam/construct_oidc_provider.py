from __future__ import annotations

import aws_cdk.aws_iam as iam
from constructs import Construct

from config.models.iam import OidcProviderConfig
from services.base import BaseServiceConstruct


class IamOidcProviderConstruct(BaseServiceConstruct):
    """
    CDK Construct for an IAM OpenID Connect (OIDC) Identity Provider.

    Required for EKS IRSA (pod-level IAM roles via service account annotations),
    GitHub Actions OIDC (keyless CI/CD), and any other workload identity
    federation scenario that uses OIDC tokens.

    After the provider is created, roles can reference it as a federated
    principal in their trust policy using::

        assumed_by:
          type: federated
          principal: <oidc_provider_url>
          conditions:
            StringEquals:
              <url>:aud: sts.amazonaws.com

    Thumbprints are optional in recent CDK versions — AWS fetches them
    automatically for well-known providers.  Supply them explicitly when
    working with private or self-managed OIDC endpoints.
    """

    def __init__(self, scope: Construct, config: OidcProviderConfig, name_prefix: str = "") -> None:
        cid = f"{name_prefix}-{config.construct_id}" if name_prefix else config.construct_id
        super().__init__(scope, cid, config)

    def _create_resource(self) -> None:
        config: OidcProviderConfig = self._config

        kwargs = dict(
            url=config.url,
            client_ids=config.client_ids,
        )
        if config.thumbprints:
            kwargs["thumbprints"] = config.thumbprints

        iam.OpenIdConnectProvider(self, "Resource", **kwargs)
