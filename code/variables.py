# -*- coding: utf8 -*-

import os

from loguru import logger

# Discord variables
DISCORD_GUILD = os.environ.get("DISCORD_GUILD", None)
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", None)
DISCORD_ROLE = os.environ.get("DISCORD_ROLE", None)

if DISCORD_GUILD:
    logger.success('DISCORD_GUILD is set')

if DISCORD_TOKEN:
    logger.success('DISCORD_TOKEN is set')
else:
    logger.warning('DISCORD_TOKEN is not set')
    exit

if DISCORD_ROLE:
    logger.success('DISCORD_ROLE is set')
else:
    logger.warning('DISCORD_ROLE is not set')
    exit
