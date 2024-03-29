#!/usr/bin/env python3
# -*- coding: utf8 -*-

import discord
import time

from loguru import logger

from subcommands import (
    diskube,
    kubectl,
    )
from variables import (
    DISCORD_GUILD,
    DISCORD_TOKEN,
    )

try:
    if DISCORD_GUILD:
        bot = discord.Bot(debug_guilds=[DISCORD_GUILD])
    else:
        bot = discord.Bot()
except Exception as e:
    logger.error(f'Discord connection KO [{e}]')
else:
    logger.info('Discord connection OK')


@bot.event
async def on_ready():
    logger.info(f'Discord on_ready OK ({bot.user})')


# Additionnal error detector to answer properly
@bot.event
async def on_application_command_error(ctx, error):
    """Inform user of errors."""
    if isinstance(error, discord.ext.commands.NoPrivateMessage):
        await ctx.respond(
            "Sorry, this can't be done in DMs.",
            ephemeral=True
            )
    elif isinstance(error, discord.ext.commands.MissingPermissions):
        await ctx.respond(
            "Sorry, you don't have permission to do this.",
            ephemeral=True
            )
    elif isinstance(error, discord.ext.commands.MissingAnyRole):
        await ctx.respond(
            "Sorry, you don't have the role to do this.",
            ephemeral=True
            )
    elif isinstance(error, discord.ext.commands.CommandNotFound):
        await ctx.respond(
            "Sorry, unable to find the proper interaction.",
            ephemeral=True
            )
    else:
        raise error


#
# /diskube Commands (aka the bot commands)
#
try:
    group_diskube = bot.create_group(
        description="Commands related to bot own actions",
        name='diskube',
        )
except Exception as e:
    logger.error(f'[{group_diskube}] Command Group KO [{e}]')
else:
    logger.debug(f'[{group_diskube}] Command Group OK')
    try:
        diskube.settings(group_diskube, bot)
    except Exception as e:
        logger.error(f'[{group_diskube}] Subcommands KO [{e}]')
    else:
        logger.debug(f'[{group_diskube}] Subcommands OK')


#
# /kubectl Commands (aka tha main commands)
#
try:
    group_kubectl = bot.create_group(
        description="Commands related to classic kubectl actions",
        name='kubectl',
        )
except Exception as e:
    logger.error(f'[{group_kubectl}] Command Group KO [{e}]')
else:
    logger.debug(f'[{group_kubectl}] Command Group OK')
    try:
        kubectl.apply(group_kubectl, bot)
        kubectl.config(group_kubectl, bot)
        kubectl.delete(group_kubectl, bot)
        kubectl.exec(group_kubectl, bot)
        kubectl.get(group_kubectl, bot)
        kubectl.logs(group_kubectl, bot)
    except Exception as e:
        logger.error(f'[{group_kubectl}] Subcommands KO [{e}]')
    else:
        logger.debug(f'[{group_kubectl}] Subcommands OK')


# Run Discord bot
iter = 0
while iter < 5:
    try:
        bot.run(DISCORD_TOKEN)
        break
    except Exception as e:
        logger.error(f'Discord bot.run KO (Attempt: {iter+1}/5) [{e}]')
        iter += 1
        time.sleep(5)
        continue
