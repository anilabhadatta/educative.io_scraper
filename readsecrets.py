import hvac


def all_secrets(client, mount_point):
    """Example that lists all secrets by key at the mount point, and then prints the secrets in full"""
    secrets_list = list_secrets(client, mount_point)

    secrets = [get_secret(client, mount_point, secret)
               for secret in secrets_list]

    return secrets


def list_secrets(client, mount_point, path=""):
    list_response = client.secrets.kv.v2.list_secrets(
        mount_point=mount_point,
        path=path
    )

    return list_response["data"]["keys"]


def get_secret(client, mount_point, path=""):
    try:
        secret_response = client.secrets.kv.v2.read_secret_version(
            mount_point=mount_point,
            path=path
        )

        return secret_response["data"]["data"]
    except hvac.exceptions.InvalidPath as err:
        print(f"Error - {err}")
