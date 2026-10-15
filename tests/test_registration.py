# -*- coding: utf8 -*-
"""Command groups and subcommands are registered as main.py expects."""

import pytest


def subcommands(bot, group_name):
    group = next(c for c in bot.pending_application_commands if c.name == group_name)
    return {c.name: c for c in group.subcommands}


def test_groups(bot):
    assert {c.name for c in bot.pending_application_commands} == {'diskube', 'kubectl'}


def test_diskube_subcommands(bot):
    assert set(subcommands(bot, 'diskube')) == {'settings'}


def test_kubectl_subcommands(bot):
    assert set(subcommands(bot, 'kubectl')) == {
        'apply', 'config', 'delete', 'exec', 'get', 'logs',
    }


@pytest.mark.parametrize('group_name, name', [
    ('diskube', 'settings'),
    ('kubectl', 'apply'),
    ('kubectl', 'config'),
    ('kubectl', 'delete'),
    ('kubectl', 'exec'),
    ('kubectl', 'get'),
    ('kubectl', 'logs'),
])
def test_commands_are_guarded(command, group_name, name):
    """Every command is guild only and requires DISCORD_ROLE (two checks)."""
    assert len(command(group_name, name).checks) == 2


@pytest.mark.parametrize('name, options', [
    ('apply', ['namespace']),
    ('config', ['subcommand']),
    ('delete', ['namespace', 'resource', 'resource_name']),
    ('exec', ['namespace', 'container', 'command']),
    ('get', ['namespace', 'resource']),
    ('logs', ['namespace', 'container']),
])
def test_kubectl_options(command, name, options):
    assert [o.name for o in command('kubectl', name).options] == options


def test_get_resource_choices(command):
    resource = command('kubectl', 'get').options[1]
    assert [c.name for c in resource.choices] == ['deployments', 'pods', 'pvc', 'services']
