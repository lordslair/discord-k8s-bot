# -*- coding: utf8 -*-

import os

from loguru import logger

# Discord variables
DISCORD_GUILD = os.environ.get("DISCORD_GUILD", None)
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", None)
DISCORD_ROLE = os.environ.get("DISCORD_ROLE", None)

K8S_NAMESPACES = os.environ.get("K8S_NAMESPACES", None)

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

if K8S_NAMESPACES:
    K8S_NAMESPACES = K8S_NAMESPACES.split(",")
    logger.success('K8S_NAMESPACES is set')
