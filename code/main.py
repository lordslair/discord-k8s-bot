#!/usr/bin/env python3
# -*- coding: utf8 -*-

import discord
import os
import time

from loguru import logger

from subcommands import (
    kubectl,
    )

# Log Internal imports
logger.info('Imports OK')

# Discord variables
DISCORD_GUILD = os.environ.get("DISCORD_GUILD", None)
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

# Log Internal imports
logger.info('Internal ENV vars loading OK')
logger.debug(f'DISCORD_GUILD:{DISCORD_GUILD}')

try:
    if DISCORD_GUILD:
        bot = discord.Bot(debug_guilds=[DISCORD_GUILD])
    else:
        bot = discord.Bot()
except Exception as e:
    logger.error(f'Discord connection KO [{e}]')
else:
    logger.info('Discord connection OK')


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
    elif isinstance(error, discord.ext.commands.CommandNotFound):
        await ctx.respond(
            "Sorry, unable to find the proper interaction.",
            ephemeral=True
            )
    else:
        raise error


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
    kubectl.delete(group_kubectl, bot)
    kubectl.get(group_kubectl, bot)
except Exception as e:
    logger.error(f'[{group_kubectl}] Command Group KO [{e}]')
else:
    logger.debug(f'[{group_kubectl}] Commands OK')


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
