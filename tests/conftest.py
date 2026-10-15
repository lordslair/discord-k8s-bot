# -*- coding: utf8 -*-
"""
Shared fixtures.

No test talks to Discord or Kubernetes:
- commands are registered on a real discord.Bot (no token, never run),
  then their callbacks are called directly with a fake context;
- the Kubernetes API classes are replaced by mocks returning real
  kubernetes.client model objects.
"""

import asyncio
import importlib
import os

import discord
import kubernetes
import pytest

from unittest.mock import AsyncMock, MagicMock

# Mandatory variables: without them, variables.py exits when the bot code is imported
os.environ.setdefault('DISCORD_TOKEN', 'test-token')
os.environ.setdefault('DISCORD_ROLE', 'test-role')

from subcommands import diskube, kubectl  # noqa: E402


@pytest.fixture(autouse=True)
def no_kubeconfig(monkeypatch):
    """Never read a real kubeconfig file."""
    monkeypatch.setattr(kubernetes.config, 'load_kube_config', MagicMock())


@pytest.fixture(autouse=True)
def empty_pods_cache():
    """Autocomplete pod lists cache: never shared between tests (nor their event loops)."""
    cache = importlib.import_module('subcommands.kubectl._autocomplete')._pods_cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def core_api(monkeypatch):
    """Mocked CoreV1Api instance (pods, services, pvc, namespaces, logs)."""
    api = MagicMock()
    monkeypatch.setattr(kubernetes.client, 'CoreV1Api', MagicMock(return_value=api))
    return api


@pytest.fixture
def apps_api(monkeypatch):
    """Mocked AppsV1Api instance (deployments)."""
    api = MagicMock()
    monkeypatch.setattr(kubernetes.client, 'AppsV1Api', MagicMock(return_value=api))
    return api


@pytest.fixture
def ctx():
    """Fake ApplicationContext: records every answer sent to Discord."""
    ctx = MagicMock()
    ctx.channel.name = 'channel'
    ctx.author.name = 'author'
    ctx.defer = AsyncMock()
    ctx.respond = AsyncMock()
    ctx.interaction.edit_original_response = AsyncMock()
    return ctx


@pytest.fixture
def loop():
    """
    One event loop per test, shared by the bot and the commands.

    discord.Bot() would otherwise call asyncio.get_event_loop(), which fails
    once a previous asyncio.run() has closed the current loop.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def bot(loop):
    """Bot with both command groups registered, as in main.py."""
    bot = discord.Bot(loop=loop)

    group_diskube = bot.create_group(name='diskube', description='diskube')
    diskube.settings(group_diskube, bot)

    group_kubectl = bot.create_group(name='kubectl', description='kubectl')
    for register in (
        kubectl.apply,
        kubectl.config,
        kubectl.delete,
        kubectl.exec,
        kubectl.get,
        kubectl.logs,
    ):
        register(group_kubectl, bot)

    return bot


@pytest.fixture
def command(bot):
    """Return a registered slash command: command('kubectl', 'get')."""
    def _command(group_name, name):
        group = next(c for c in bot.pending_application_commands if c.name == group_name)
        return next(c for c in group.subcommands if c.name == name)
    return _command


@pytest.fixture
def run(command, ctx, loop):
    """Run a command callback: run('kubectl', 'get', 'default', 'pods')."""
    def _run(group_name, name, *args):
        loop.run_until_complete(command(group_name, name).callback(ctx, *args))
    return _run
