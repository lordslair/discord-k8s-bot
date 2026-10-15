# Diskube (aka discord-k8s-bot), the project :

TLDR; This is a Python **very simple** Discord bot to pilot/orchestrate a (one) Kubernetes Cluster and its resources.  

### Variables

To work properly, the bot will require informations and credentials to contact ant operate Kubernetes requests.  
We assume they are passed to the container in ENV variables.

Discord variables :
Mandatory ones:
- `DISCORD_TOKEN`: The Discord Token to run the bot. (Refer to Discord docs for details about it)
- `DISCORD_ROLE`:  The Discord rolename needed to be able to use the bot commands
Optional ones:
- `DISCORD_GUILD`: The Discord GuildId to restrict bot propagation. (Defaults: `None`)

Kubernetes variables :
Optional ones:
- `K8S_NAMESPACES`: Comma-separated namespaces offered in commands autocomplete, e.g. `default,prod`. They are offered as is, without querying the cluster: fast, and works when the bot isn't allowed to list namespaces cluster-wide. (Defaults: `None`, all namespaces, listed from the cluster)
- `K8S_LOGS_TAIL_LINES`: Number of log lines fetched by `/kubectl logs`. The latest ones that fit are shown in the message, and when they don't all fit, all fetched lines are attached as a `.log` file. (Defaults: `200`)

ENV global variables :
- `LOGURU_LEVEL`: Minimal level for log output (Default: `DEBUG`)  


Security warning :  
`DISCORD_TOKEN` is meant to be kept as ENVVAR to avoid having it clearly hardcoded somewhere.  
Keep in mind that's a **very** important thing to keep secret. Do not post it anywhere publicly.  
Don't blame the project if you fail with this.  

### Config file

The bot expects to find inside the Container one kubeconfig file here: `/etc/k8s/kubeconfig.yaml`.  
You can populate this file via a local mount with Docker, of via a configMap with Kubernetes.  
To use another path, set `KUBECONFIG_FILE`.  
If the file can't be loaded, commands answer `Command aborted: K8s config KO`.  

The bot is designed to handle one kubeconfig file containing one Cluster.  
Weird behaviour may happen if you don't respect that rule.  

### SlashCommands

All commands only work in a server (not in DMs), for members with the `DISCORD_ROLE` role.  
Answers are only visible to the member who used the command.  
Options offer autocomplete: namespaces (limited to `K8S_NAMESPACES` if set), pods, and containers (shown as `<name or app label>/<container>`).  
Discord shows 25 suggestions at most: type part of a name to narrow the list.  
Pod and container suggestions are cached for 5 seconds per namespace, so a pod created or deleted outside the bot just now may take a few seconds to show up (or disappear) there. A pod deleted with `/kubectl delete` disappears at once. Commands themselves always query the cluster.

| Command | Options | Does |
|---------|---------|------|
| `/diskube settings` | – | Show the bot version and settings |
| `/kubectl config` | `show` | Show the cluster name and API server |
| `/kubectl get` | namespace, `deployments` / `pods` / `pvc` / `services` | List resources and their status |
| `/kubectl logs` | namespace, container | Show the latest log lines of a container |
| `/kubectl exec` | namespace, container, command | Run a command in a container |
| `/kubectl delete` | namespace, `pod`, pod name | Delete a pod |
| `/kubectl apply` | namespace | Not implemented yet |

#### Examples

`/diskube settings`
```
Version:
> Release: 1.2.3
> Commit: 11fe7b7
ENV Vars:
> KUBECONFIG_FILE: /etc/k8s/kubeconfig.yaml
> DISCORD_GUILD: None
> DISCORD_ROLE: Team
```

`/kubectl config show`
```
Cluster:
> Name: my-cluster
> Server: https://k8s.example.com:6443
```

`/kubectl get namespace:backend resource:pods` (🟩 ready / 🟥 not ready, restart count in brackets; CronJob pods are skipped)
```
web-5d8f7c6b9-x2x4z
> 🟩 nginx (0)
api-7c9d4b8f5-q8w2m
> 🟥 api (3)
> 🟩 proxy (1)
```

`/kubectl get namespace:backend resource:deployments` (available / wanted replicas)
```
🟩 web (2/2)
🟥 api (1/3)
```

`/kubectl get namespace:backend resource:pvc` (🟩 bound, size; ⬜ otherwise, size or phase)
```
🟩 data (10Gi)
⬜ cache (Pending)
```

`/kubectl get namespace:backend resource:services` (LoadBalancers also show their address, or `<pending>`)
```
web (ClusterIP)
> 10.0.0.1:80 -> http:8080
lb (LoadBalancer)
> 10.0.0.2:443 -> https:8443
> hostname: lb.example.com
```

`/kubectl logs namespace:backend container:api/api` (ANSI colours removed, a level emoji per line)
```
🟩 INFO  Server started on :8080
🟦 DEBUG Loaded 12 routes
🟧 WARN  Slow query (1.2s)
🟥 ERROR Upstream timeout
⬜ GET /health 200
```
Only the latest lines that fit in one Discord message are shown. When the fetched log (last `K8S_LOGS_TAIL_LINES` lines) doesn't fit, it is also attached as `<pod>-<container>.log`.

`/kubectl exec namespace:backend container:api/api command:ls -l /tmp`
```
> ls -l /tmp
total 0
```

`/kubectl delete namespace:backend resource:pod resource_name:api-7c9d4b8f5-q8w2m`
```
The pod api-7c9d4b8f5-q8w2m was terminated.
```

Errors are answered in red, for example `Command aborted: K8s Query KO` when the cluster can't be queried.

### Output on server start

```
2023-11-24 15:31:57 | level=SUCCESS  | variables:<module>:16 - DISCORD_TOKEN is set
2023-11-24 15:31:57 | level=SUCCESS  | variables:<module>:22 - DISCORD_ROLE is set
2023-11-24 15:31:59 | level=INFO     | __main__:<module>:26 - Discord connection OK
2023-11-24 15:31:59 | level=DEBUG    | __main__:<module>:68 - [diskube] Command Group OK
2023-11-24 15:31:59 | level=DEBUG    | __main__:<module>:74 - [diskube] Subcommands OK
2023-11-24 15:31:59 | level=DEBUG    | __main__:<module>:88 - [kubectl] Command Group OK
2023-11-24 15:31:59 | level=DEBUG    | __main__:<module>:98 - [kubectl] Subcommands OK
```

### Tech

I mainly used :

* [Pycord-Development/pycord][pycord] as rich Discord API wrapper in Python
* [docker/docker-ce][docker] to make it easy to maintain
* [kubernetes/kubernetes][kubernetes] to make everything smooth
* [Alpine][alpine] - probably the best/lighter base container to work with
* [Python] - as usual
* [Delgan/loguru][loguru] - an amazingly powerful logger

And of course GitHub to store all these shenanigans.

### Installation

You can build the container yourself :
```
$ git clone https://github.com/lordslair/discord-k8s-bot
$ cd discord-k8s-bot
$ docker build .
```

Or the latest build is available on [Docker hub][hub]: `lordslair/discord-k8s-bot`:
```
$ docker pull lordslair/discord-k8s-bot:latest
latest: Pulling from lordslair/discord-k8s-bot
Digest: sha256:4a9bb27c95f1a37a114547836a0c8d2571834d31625d32cef860a5c3253f8517
Status: Downloaded newer image for lordslair/discord-k8s-bot:latest
docker.io/lordslair/discord-k8s-bot:latest
```

#### Tests

Tests live in `tests/` and run with [pytest][pytest]. They need no Discord token and no Kubernetes cluster:
both are faked, so they also run in CI on pull requests.
```
$ pip install -r requirements.txt -r requirements-tests.txt
$ pytest
```

Known bugs have a test marked `xfail(strict=True)`, describing the expected behaviour.
Once a bug is fixed, its test starts failing (XPASS): remove the marker.

#### GitHub Actions pipelines

- **Pipeline Tests**: on every push / PR to `master`, runs lint (flake8) and tests (pytest), then builds the image.
Only pushes to `master` publish it to Docker Hub, as `edge` and the short commit SHA.
- **Pipeline Release**: on push of a `v*` tag, runs lint and tests, then publishes `X.Y.Z`, `X.Y`, the short commit SHA and `latest`.

Details and conventions: [.github/workflows/WORKFLOWS.md](.github/workflows/WORKFLOWS.md)

#### Disclaimer/Reminder

> Always store somewhere safe your DISCORD_TOKEN.  
> I won't take any blame if you mess up somewhere in the process =)  

### Resources / Performance

The container is quite light, as [Alpine][alpine] is used as base.  

```
$ docker images
REPOSITORY                 TAG       SIZE
lordslair/discord-k8s-bot  latest    162MB
```

On the performance topic, the container consumes about :
 - 0,01% of a CPU at rest
 - 64MB of RAM

### Todos

They will be added as PR here: https://github.com/lordslair/discord-k8s-bot/pulls  
I'm open to requests/comments/ideas/issues in PR section.  

---
   [alpine]: <https://github.com/alpinelinux>
   [docker]: <https://github.com/docker/docker-ce>
   [kubernetes]: <https://github.com/kubernetes/kubernetes>
   [pycord]: <https://github.com/Pycord-Development/pycord>
   [loguru]: <https://github.com/Delgan/loguru>
   [python]: <https://www.python.org>
   [pytest]: <https://docs.pytest.org>
   [hub]: <https://hub.docker.com/repository/docker/lordslair/discord-k8s-bot>
