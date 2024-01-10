# -*- coding: utf8 -*-

import discord

from discord.commands import option
from discord.ext import commands
from kubernetes import config, client
from kubernetes.stream import stream
from loguru import logger

from subcommands.kubectl._autocomplete import (
    k8s_list_namespace,
    k8s_list_namespaced_resources,
    k8s_list_pod_containers,
)
from variables import DISCORD_ROLE


def exec(group_kubectl, bot):
    @group_kubectl.command(
        description='Execute a command in a container.',
        default_permission=False,
        name='exec',
        )
    @commands.guild_only()  # Hides the command from the menu in DMs
    @commands.has_any_role(DISCORD_ROLE)
    @option(
        "namespace",
        description="Namespace",
        autocomplete=k8s_list_namespace
        )
    @option(
        "resource",
        description="Resource type",
        choices=[
            discord.OptionChoice('pod'),
            ],
        )
    @option(
        "resource_name",
        description="Resource name",
        autocomplete=k8s_list_namespaced_resources,
        )
    @option(
        "subresource_name",
        description="Sub-resource name",
        autocomplete=k8s_list_pod_containers,
        )
    @option(
        "command",
        description="Command to execute",
        )
    async def get(
        ctx,
        namespace: str,
        resource: str,
        resource_name: str,
        subresource_name: str,
        command: str,
    ):
        await ctx.defer(ephemeral=True)  # To defer answer (default: 15min)
        logger.info(
            f'[#{ctx.channel.name}][{ctx.author.name}] '
            f'/{group_kubectl} exec {resource_name} {subresource_name} {command} [{namespace}]'
            )

        try:
            config.load_kube_config("/etc/k8s/kubeconfig.yaml")
        except Exception as e:
            logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Load KO [{e}]')
        else:
            pass

        if (
            resource == 'pod'
            and resource_name is not None
            and subresource_name is not None
            and command is not None
        ):
            try:

                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query')
                exec_stdout = stream(
                    client.CoreV1Api().connect_get_namespaced_pod_exec,
                    resource_name,
                    namespace,
                    container=subresource_name,
                    command=command.split(),
                    stderr=True, stdin=False,
                    stdout=True, tty=False,
                    )
                logger.trace(exec_stdout)
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query Ended')
            except Exception as e:
                msg = f'K8s exec KO [{e}]'
                logger.error(msg)
                embed = discord.Embed(
                    description=msg,
                    colour=discord.Colour.red()
                    )
                await ctx.respond(embed=embed)
                return
            else:
                await ctx.interaction.edit_original_response(
                    embed=discord.Embed(
                        title='K8s exec',
                        description=f'> `{command}`\n```{exec_stdout}```',
                        colour=discord.Colour.green()
                        )
                    )
        else:
            pass
