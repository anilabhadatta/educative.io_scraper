def write_secret(client, secret, mount_point, path=""):
    write_response = client.secrets.kv.v2.create_or_update_secret(
        mount_point=mount_point,
        path=path,
        secret=secret
    )

    return write_response["data"]
