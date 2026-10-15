# -*- coding: utf8 -*-

import discord
import io
import re

from discord.commands import option
from discord.ext import commands
from kubernetes import client
from loguru import logger

from subcommands.kubectl._autocomplete import (
    k8s_list_namespace,
    k8s_list_namespaced_containers,
    split_container,
)
from subcommands.kubectl._kubeconfig import load_kubeconfig
from variables import DISCORD_ROLE, K8S_LOGS_TAIL_LINES

# Discord message limit, minus the ``` wrapper on both sides
MESSAGE_BUDGET = 2000 - 6
# ANSI sequences (ex: colors)
ANSI_ESCAPE = re.compile(r'\x1b[^m]*m')


def level_prefix(line):
    if 'WARN' in line.upper():
        return '🟧'
    elif 'ERROR' in line.upper():
        return '🟥'
    elif 'INFO' in line.upper():
        return '🟩'
    elif 'DEBUG' in line.upper():
        return '🟦'
    elif 'TRACE' in line.upper():
        return '🟦'
    else:
        return '⬜'


def format_logs(log):
    """
    Latest log lines that fit in one Discord message, oldest first.

    Returns (content, complete): complete is False when lines were left out
    or the latest line had to be shortened.
    """
    lines = []
    length = 0
    complete = True
    for line in reversed(log.splitlines()):
        prefix = f'{level_prefix(line)} '
        newline = f'{prefix}{line}\n'
        if length + len(newline) > MESSAGE_BUDGET:
            complete = False
            if not lines:
                # Even the latest line alone is too long: keep its start
                room = MESSAGE_BUDGET - len(prefix) - len('…\n')
                lines.append(f'{prefix}{line[:room]}…\n')
            break
        lines.append(newline)
        length += len(newline)

    return '```' + ''.join(reversed(lines)) + '```', complete


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
        autocomplete=k8s_list_namespace,
        )
    @option(
        "container",
        description="Container to target",
        autocomplete=k8s_list_namespaced_containers,
        )
    async def logs(
        ctx,
        namespace: str,
        container: str,
    ):
        await ctx.defer(ephemeral=True)  # To defer answer (default: 15min)

        try:
            (pod_name, container_name) = split_container(container)
        except ValueError as e:
            logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> Invalid container [{e}]')
            await ctx.respond(
                embed=discord.Embed(
                    description=f'Invalid container `{container}`: pick one from the list.',
                    colour=discord.Colour.red()
                    )
                )
            return

        logger.info(
            f'[#{ctx.channel.name}][{ctx.author.name}] '
            f'/{group_kubectl} logs {pod_name} {container_name} [{namespace}]'
            )

        if not await load_kubeconfig(ctx):
            return

        if pod_name is not None and container_name is not None:
            try:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query')
                log = client.CoreV1Api().read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    container=container_name,
                    tail_lines=K8S_LOGS_TAIL_LINES,
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
                log_purged = ANSI_ESCAPE.sub('', log)
                content, complete = format_logs(log_purged)

                if complete:
                    await ctx.interaction.edit_original_response(content=content)
                else:
                    # Not everything fits in the message: attach the fetched log as a file
                    await ctx.interaction.edit_original_response(
                        content=content,
                        file=discord.File(
                            io.BytesIO(log_purged.encode()),
                            filename=f'{pod_name}-{container_name}.log',
                            ),
                        )
            else:
                await ctx.respond(
                    embed=discord.Embed(
                        title=f'kubectl logs {container_name} [{namespace}]',
                        description='No logs available',
                        colour=discord.Colour.green()
                        ),
                    )

            return
        else:
            pass
