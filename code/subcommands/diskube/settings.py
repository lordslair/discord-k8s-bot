# -*- coding: utf8 -*-

import discord
import os

from discord.ext import commands
from loguru import logger

from variables import DISCORD_ROLE


def settings(group_diskube, bot):
    @group_diskube.command(
        description='Display Diskube actual settings.',
        default_permission=False,
        name='settings',
        )
    @commands.guild_only()  # Hides the command from the menu in DMs
    @commands.has_any_role(DISCORD_ROLE)
    async def settings(
        ctx,
    ):
        await ctx.defer(ephemeral=True)  # To defer answer (default: 15min)
        logger.info(
            f'[#{ctx.channel.name}][{ctx.channel.name}] /{group_diskube} settings'
            )

        KUBECONFIG_FILE = os.environ.get("KUBECONFIG_FILE", "/etc/k8s/kubeconfig.yaml")
        DISCORD_GUILD = os.environ.get("DISCORD_GUILD", None)

        description = (
            f"ENV Vars:\n"
            f"> KUBECONFIG_FILE: `{KUBECONFIG_FILE}`\n"
            f"> DISCORD_GUILD: `{DISCORD_GUILD}`\n"
            f"> DISCORD_ROLE: `{DISCORD_ROLE}`\n"
        )

        await ctx.respond(
            embed=discord.Embed(
                title='diskube settings',
                description=description,
                colour=discord.Colour.blue()
                ),
            )
        return
