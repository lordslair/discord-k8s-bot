# -*- coding: utf8 -*-

import discord
import re

from discord.commands import option
from discord.ext import commands
from kubernetes import config, client
from loguru import logger

from subcommands.kubectl._autocomplete import (
    k8s_list_namespace,
    k8s_list_namespaced_resources,
)
from variables import DISCORD_ROLE


def logs(group_kubectl, bot):
    @group_kubectl.command(
        description='Print the logs for a container in a pod.',
        default_permission=False,
        name='logs',
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
        autocomplete=k8s_list_namespaced_resources
        )
    async def logs(
        ctx,
        namespace: str,
        resource: str,
        resource_name: str,
    ):
        await ctx.defer(ephemeral=True)  # To defer answer (default: 15min)
        logger.info(
            f'[#{ctx.channel.name}][{ctx.author.name}] '
            f'/{group_kubectl} logs {resource_name} [{namespace}]'
            )

        try:
            config.load_kube_config("/etc/k8s/kubeconfig.yaml")
        except Exception as e:
            logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Load KO [{e}]')
        else:
            pass

        if resource == 'pod' and resource_name is not None:
            try:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query')
                log = client.CoreV1Api().read_namespaced_pod_log(
                    name=resource_name,
                    since_seconds=1728000,
                    namespace=namespace,
                    )
                logger.debug(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query Ended')
            except Exception as e:
                logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query KO [{e}]')
                embed = discord.Embed(
                    description='Command aborted: K8s Query KO',
                    colour=discord.Colour.red()
                    )
                await ctx.respond(embed=embed)
                return
            else:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query OK')

            if log != '':
                # We do this to filter out ANSI sequences (ex: colors)
                reaesc = re.compile(r'\x1b[^m]*m')
                log_purged = reaesc.sub('', log)

                # We do this to have the latest lines, not the first
                lines_first_to_last = []
                content_length = 0  # to count the final message length
                for line in reversed(log_purged.splitlines()):
                    if content_length + len(line) < 2000:
                        if 'WARN' in line.upper():
                            newline = f'🟧 {line}\n'
                        elif 'ERROR' in line.upper():
                            newline = f'🟥 {line}\n'
                        elif 'INFO' in line.upper():
                            newline = f'🟩 {line}\n'
                        elif 'DEBUG' in line.upper():
                            newline = f'🟦 {line}\n'
                        elif 'TRACE' in line.upper():
                            newline = f'🟦 {line}\n'
                        else:
                            newline = f'⬜ {line}\n'

                        content_length += len(newline)
                        lines_first_to_last.append(newline)
                    else:
                        break

                content = ''
                for line in reversed(lines_first_to_last):
                    content += line
                    await ctx.interaction.edit_original_response(
                        content=f'```{content}```',
                        )
            else:
                await ctx.respond(
                    embed=discord.Embed(
                        title=f'kubectl logs {resource_name} [{namespace}]',
                        description='No logs available',
                        colour=discord.Colour.green()
                        ),
                    )

            return
        else:
            pass
