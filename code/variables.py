# -*- coding: utf8 -*-

import os
import sys

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
    logger.error('DISCORD_TOKEN is not set')
    sys.exit(1)

if DISCORD_ROLE:
    logger.success('DISCORD_ROLE is set')
else:
    logger.error('DISCORD_ROLE is not set')
    sys.exit(1)

if K8S_NAMESPACES:
    # "default, prod," -> ['default', 'prod']
    K8S_NAMESPACES = [n.strip() for n in K8S_NAMESPACES.split(",") if n.strip()]
    logger.success('K8S_NAMESPACES is set')

# Number of log lines fetched by /kubectl logs
K8S_LOGS_TAIL_LINES_DEFAULT = 200
K8S_LOGS_TAIL_LINES = os.environ.get("K8S_LOGS_TAIL_LINES", None)

if K8S_LOGS_TAIL_LINES:
    try:
        K8S_LOGS_TAIL_LINES = int(K8S_LOGS_TAIL_LINES)
        if K8S_LOGS_TAIL_LINES < 1:
            raise ValueError('must be >= 1')
    except ValueError as e:
        logger.warning(
            f'K8S_LOGS_TAIL_LINES is invalid [{e}], '
            f'using default ({K8S_LOGS_TAIL_LINES_DEFAULT})'
            )
        K8S_LOGS_TAIL_LINES = K8S_LOGS_TAIL_LINES_DEFAULT
    else:
        logger.success('K8S_LOGS_TAIL_LINES is set')
else:
    K8S_LOGS_TAIL_LINES = K8S_LOGS_TAIL_LINES_DEFAULT
