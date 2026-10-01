# Production deployment

The GitHub Actions workflow builds `tools/Dockerfile`, pushes an immutable image
tag to GHCR, and deploys it to `/opt/anketa` over SSH as the `deploy` user.

## VPS preparation

The image runs as UID/GID `10001`. Create the persistent directories with a
matching host group so that the unprivileged container can write to them:

```bash
sudo groupadd --system --gid 10001 anketa || true
sudo usermod -aG anketa deploy
sudo install -d -m 0770 -o 10001 -g 10001 \
  /opt/anketa/{data,logs,session,images,questionfiles,reports}
sudo install -d -m 0750 -o deploy -g deploy /opt/anketa/shared
```

Reconnect as `deploy` after changing its groups.

Copy `deploy/app.env.example` to `/opt/anketa/shared/app.env`, fill in the
values, and protect it:

```bash
sudo chown deploy:deploy /opt/anketa/shared/app.env
sudo chmod 600 /opt/anketa/shared/app.env
```

The real bot token, API credentials, and session value must exist only in this
file or another secret manager. Do not commit them.

The `deploy` user needs Docker access. Add its public SSH key to
`/home/deploy/.ssh/authorized_keys` and add the user to the `docker` group.

## GitHub configuration

Add these repository or environment secrets:

```text
VPS_HOST
VPS_PORT
VPS_USER
VPS_SSH_PRIVATE_KEY
VPS_KNOWN_HOSTS
GHCR_READ_TOKEN
```

Store the hostname and SSH port separately, for example `VPS_HOST=host.com`
and `VPS_PORT=2288`. Do not include the port in `VPS_HOST`.

`GHCR_READ_TOKEN` is a GitHub Personal Access Token (classic) with the
`read:packages` scope. It is used by the VPS to pull the private image from
GHCR. The token owner must have access to the package; authorize it for the
organization if GitHub requires SSO.

`GHCR_READ_TOKEN` needs `read:packages` access. Configure the `production`
environment with required reviewers if manual approval is desired.
