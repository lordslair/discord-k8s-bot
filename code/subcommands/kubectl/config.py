# -*- coding: utf8 -*-

import discord
import os
import yaml

from discord.commands import option
from discord.ext import commands
from loguru import logger


def config(group_kubectl, bot):
    @group_kubectl.command(
        description='Show Cluster configuration.',
        default_permission=False,
        name='config',
        )
    @commands.guild_only()  # Hides the command from the menu in DMs
    @commands.has_any_role('Team')
    @option(
        "subcommand",
        description="Subcommand",
        choices=[
            discord.OptionChoice('show'),
            ],
        )
    async def config(
        ctx,
        subcommand: str,
    ):
        await ctx.defer(ephemeral=True)  # To defer answer (default: 15min)
        logger.info(
            f'[#{ctx.channel.name}][{ctx.author.name}] '
            f'/{group_kubectl} config {subcommand}'
            )

        KUBECONFIG_FILE = os.environ.get("KUBECONFIG_FILE", "/etc/k8s/kubeconfig.yaml")
        logger.debug(f"KUBECONFIG_FILE:{KUBECONFIG_FILE}")
        if os.path.isfile(KUBECONFIG_FILE):
            try:
                with open(KUBECONFIG_FILE, 'r') as file:
                    kubeyaml = yaml.safe_load(file)
                    description = (
                        '```'
                        "Cluster:\n"
                        f"> Name: {kubeyaml['clusters'][0]['name']}\n"
                        f"> Server: {kubeyaml['clusters'][0]['cluster']['server']}\n"
                        '```'
                    )
            except Exception as e:
                logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> YAML Load KO [{e}]')
                await ctx.interaction.edit_original_response(
                    embed=discord.Embed(
                        title=f'kubectl config {subcommand}',
                        description='Unable to load YAML file.',
                        colour=discord.Colour.red()
                        )
                    )
                return
            else:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query OK')
                await ctx.interaction.edit_original_response(
                    embed=discord.Embed(
                        title=f'kubectl config {subcommand}',
                        description=description,
                        colour=discord.Colour.green()
                        )
                    )
                return
        else:
            logger.debug(f"KUBECONFIG_FILE:{KUBECONFIG_FILE} NotFound")
            logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Load KO')
            await ctx.interaction.edit_original_response(
                embed=discord.Embed(
                    title=f'kubectl config {subcommand}',
                    description='YAML file not found (Should be there:{KUBECONFIG_FILE}).',
                    colour=discord.Colour.red()
                    )
                )
            return
