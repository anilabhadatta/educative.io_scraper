import os
from dotenv import load_dotenv

load_dotenv()

VAULT_CLUSTER = os.getenv("vault_cluster")
SECURITY_CONTEXT = os.getenv("security_context")
CLUSTER_AWS_REGION = os.getenv("cluster_aws_region")

AUTH_NAMESPACE = os.getenv("namespace_auth")
SECRETS_NAMESPACE = os.getenv("namespace_secrets")
AUTH_AWS_REGION = os.getenv("auth_aws_region")

AUTH_AWS_PROFILE = os.getenv("auth_aws_profile")
AUTH_AWS_ROLE = os.getenv("auth_aws_role")

LDAP_USERNAME = os.getenv("auth_ldap_username")
LDAP_PASSWORD = os.getenv("auth_ldap_password")

VAULT_URL = f"https://{VAULT_CLUSTER}.{CLUSTER_AWS_REGION}.secrets.runtime.{SECURITY_CONTEXT}-cts.exp-aws.net"
