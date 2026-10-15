# -*- coding: utf8 -*-

import asyncio
import discord
import os

from kubernetes import config
from loguru import logger


def kubeconfig_file():
    return os.environ.get("KUBECONFIG_FILE", "/etc/k8s/kubeconfig.yaml")


async def load_kubeconfig(ctx):
    """
    Load the kubeconfig before a command queries the cluster.

    On failure, tell the user and return False: the command must stop there.
    """
    try:
        # Reads and parses a file: in a thread, not to block the event loop
        await asyncio.to_thread(config.load_kube_config, kubeconfig_file())
    except Exception as e:
        logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Load KO [{e}]')
        await ctx.respond(
            embed=discord.Embed(
                description='Command aborted: K8s config KO',
                colour=discord.Colour.red()
                )
            )
        return False
    return True
