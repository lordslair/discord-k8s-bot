# -*- coding: utf8 -*-
"""/kubectl logs: log formatting and Discord's 2000 characters limit."""

import discord
import pytest

from helpers import embed


def final_content(ctx):
    """Message content after the last edit."""
    return ctx.interaction.edit_original_response.call_args.kwargs['content']


def test_calls_api_with_pod_and_container(run, core_api):
    core_api.read_namespaced_pod_log.return_value = 'line\n'

    run('kubectl', 'logs', 'default', 'web-abc/nginx')

    core_api.read_namespaced_pod_log.assert_called_once_with(
        name='web-abc',
        since_seconds=1728000,
        namespace='default',
        container='nginx',
    )


def test_levels_and_ansi(run, ctx, core_api):
    core_api.read_namespaced_pod_log.return_value = (
        '\x1b[32mINFO\x1b[0m started\n'
        'debug: details\n'
        'Warning: slow\n'
        'ERROR failed\n'
        'TRACE x\n'
        'plain line\n'
    )

    run('kubectl', 'logs', 'default', 'web-abc/nginx')

    assert final_content(ctx) == (
        '```'
        '🟩 INFO started\n'
        '🟦 debug: details\n'
        '🟧 Warning: slow\n'
        '🟥 ERROR failed\n'
        '🟦 TRACE x\n'
        '⬜ plain line\n'
        '```'
    )


def test_keeps_latest_lines(run, ctx, core_api):
    lines = [f'line {i:04d} ' + 'x' * 90 for i in range(100)]
    core_api.read_namespaced_pod_log.return_value = '\n'.join(lines)

    run('kubectl', 'logs', 'default', 'web-abc/nginx')

    content = final_content(ctx)
    assert lines[-1] in content
    assert lines[0] not in content
    assert len(content) <= 2000


@pytest.mark.xfail(strict=True,
                   reason='Limit checks len(line), not the added prefix + ``` wrapper')
def test_never_exceeds_discord_limit(run, ctx, core_api):
    core_api.read_namespaced_pod_log.return_value = 'x' * 1999

    run('kubectl', 'logs', 'default', 'web-abc/nginx')

    assert len(final_content(ctx)) <= 2000


def test_no_logs(run, ctx, core_api):
    core_api.read_namespaced_pod_log.return_value = ''

    run('kubectl', 'logs', 'default', 'web-abc/nginx')

    result = embed(ctx.respond)
    assert result.title == 'kubectl logs nginx [default]'
    assert result.description == 'No logs available'


def test_api_error(run, ctx, core_api):
    core_api.read_namespaced_pod_log.side_effect = Exception('boom')

    run('kubectl', 'logs', 'default', 'web-abc/nginx')

    result = embed(ctx.respond)
    assert result.description == 'Command aborted: K8s Query KO'
    assert result.colour == discord.Colour.red()
