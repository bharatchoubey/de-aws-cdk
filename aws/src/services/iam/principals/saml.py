from __future__ import annotations

import aws_cdk.aws_iam as iam

from config.models.iam import AssumedByConfig
from services.iam.principals.base import BasePrincipal


class SamlPrincipal(BasePrincipal):
    """
    Builds an IAM FederatedPrincipal for SAML 2.0 identity providers.

    Use when a role should be assumed via enterprise SSO (Okta, Azure AD,
    PingFederate, etc.) using SAML 2.0 federation.

    The ``principal`` must be the full ARN of an existing SAML provider
    (``arn:aws:iam::<account>:saml-provider/<name>``).

    Example config::

        assumed_by:
          type: saml
          principal: arn:aws:iam::123456789012:saml-provider/MyOktaProvider
          conditions:
            StringEquals:
              SAML:aud: https://signin.aws.amazon.com/saml
    """

    def build(self, config: AssumedByConfig) -> iam.IPrincipal:
        return iam.FederatedPrincipal(
            federated=config.principal,
            conditions=config.conditions,
            assume_role_action="sts:AssumeRoleWithSAML",
        )
