import hvac

# from envvars import SECRETS_NAMESPACE, AUTH_NAMESPACE, VAULT_URL, LDAP_PASSWORD, LDAP_USERNAME
from readsecrets import all_secrets
from writesecrets import write_secret


def ldap_auth_example():
    ENV = "lab"
    DOMAIN = "data"
    # Create HVAC client with authentication namespace to Authenticate with either LDAP, or an AWS IAM role
    client = hvac.Client(url="https://vault-enterprise.us-west-2.secrets.runtime.test-cts.exp-aws.net",
                         verify=False, namespace="{ENV}")
    login_to_vault_ldap(client)

    # Change namespace to secrets namespace, ie where secrets are actually stored
    client.adapter.namespace = "{ENV}/islands/{DOMAIN}"

    # Use authenticated HVAC client to manipulate Vault
    # write_secret(client, secret={"user": "admin", "password": "12345"}, mount_point="example", path="mysecret")
    return all_secrets(client, "example")


def login_to_vault_ldap(client):
    client.auth.ldap.login(
        username="amisra",
        password=""
    )


ldap_auth_example()
