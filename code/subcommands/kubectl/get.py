# -*- coding: utf8 -*-

import discord

from discord.commands import option
from discord.ext import commands
from kubernetes import config, client
from loguru import logger

from subcommands.infra._autocomplete import k8s_list_namespace

def get(group_kubectl):
    @group_kubectl.command(
        description='Display one or many resources.',
        default_permission=False,
        name='get',
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
            discord.OptionChoice('Deployments'),
            discord.OptionChoice('Pods'),
            discord.OptionChoice('Services'),
            ],
        )
    async def get(
        ctx,
        namespace: str,
        resource: str,
    ):
        await ctx.defer()  # To defer answer (default: 15min)
        logger.info(
            f'[#{ctx.channel.name}][{ctx.channel.name}] '
            f'/{group_kubectl} get {namespace} {resource}'
            )

        try:
            config.load_kube_config(f"/etc/kubeconfig.yaml")
        except Exception as e:
            logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Load KO [{e}]')
        else:
            pass

        if resource == 'Pods':
            try:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query Starting')
                resource = client.CoreV1Api().list_namespaced_pod(namespace)
                logger.debug(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query Ended')
            except Exception as e:
                logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query KO [{e}]')
                embed = discord.Embed(
                    description='Command aborted: K8s Query KO',
                    colour=discord.Colour.red()
                    )
                await ctx.respond(embed=embed)
                return
        elif resource == 'Deployments':
            pass
        elif resource == 'Services':
            pass
        else:
            pass
