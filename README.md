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

ENV global variables :
- `LOGURU_LEVEL`: Minimal level for log output (Default: `DEBUG`)  


Security warning :  
`DISCORD_TOKEN` is meant to be kept as ENVVAR to avoid having it clearly hardcoded somewhere.  
Keep in mind that's a **very** important thing to keep secret. Do not post it anywhere publicly.  
Don't blame the project if you fail with this.  

### Config file

The bot expects to find inside the Container one kubeconfig file here: `/etc/k8s/kubeconfig.yaml`.  
You can populate this file via a local mount with Docker, of via a configMap with Kubernetes.  

The bot is designed to handle one kubeconfig file containing one Cluster.  
Weird behaviour may happen if you don't respect that rule.  

### Screenshots

This needs yet to be done.  

### SlashCommands

This needs yet to be done. 

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

This needs yet to be done.  

#### Disclaimer/Reminder

> Always store somewhere safe your DISCORD_TOKEN.  
> I won't take any blame if you mess up somewhere in the process =)  

### Resources / Performance

The container is quite light, as [Alpine][alpine] is used as base.  

```
$ docker images
REPOSITORY                 TAG       SIZE
lordslair/discord-k8s-bot  latest    126MB
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
   [hub]: <https://hub.docker.com/repository/docker/lordslair/discord-k8s-bot>
