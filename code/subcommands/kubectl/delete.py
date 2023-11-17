# -*- coding: utf8 -*-

import discord

from discord.commands import option
from discord.ext import commands
from kubernetes import config, client
from loguru import logger

from subcommands.kubectl._autocomplete import (
    k8s_list_namespace,
    k8s_list_namespaced_resources,
)


def delete(group_kubectl, bot):
    @group_kubectl.command(
        description='Display one or many resources.',
        default_permission=False,
        name='delete',
        )
    @commands.guild_only()  # Hides the command from the menu in DMs
    @commands.has_any_role('Team')
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
    async def delete(
        ctx,
        namespace: str,
        resource: str,
        resource_name: str,
    ):
        await ctx.defer(ephemeral=True)  # To defer answer (default: 15min)
        logger.info(
            f'[#{ctx.channel.name}][{ctx.channel.name}] '
            f'/{group_kubectl} delete {namespace} {resource} {resource_name}'
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
                client.CoreV1Api().delete_namespaced_pod(resource_name, namespace)
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

            # We got the resources object, we can start working
            embed = discord.Embed(
                title=f'kubectl delete {resource} [{namespace}]',
                description=f'The {resource} `{resource_name}` was terminated.',
                colour=discord.Colour.green()
                )

            # We Start to update the Embed
            await ctx.interaction.edit_original_response(embed=embed)
            return
        else:
            pass
