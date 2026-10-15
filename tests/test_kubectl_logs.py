# -*- coding: utf8 -*-
"""/kubectl logs: log formatting, Discord's 2000 characters limit, full log as a file."""

import discord
import pytest

from helpers import embed, module

logs = module('subcommands.kubectl.logs')


def sent(ctx):
    """kwargs of the single message edit."""
    ctx.interaction.edit_original_response.assert_called_once()
    return ctx.interaction.edit_original_response.call_args.kwargs


def attached(kwargs):
    """(filename, text) of the attached file."""
    file = kwargs['file']
    assert isinstance(file, discord.File)
    return file.filename, file.fp.getvalue().decode()


# API call

def test_calls_api_with_pod_container_and_tail_lines(run, core_api):
    core_api.read_namespaced_pod_log.return_value = 'line\n'

    run('kubectl', 'logs', 'default', 'web-abc/nginx')

    core_api.read_namespaced_pod_log.assert_called_once_with(
        name='web-abc',
        namespace='default',
        container='nginx',
        tail_lines=200,
    )


def test_tail_lines_from_variable(monkeypatch, run, core_api):
    monkeypatch.setattr(logs, 'K8S_LOGS_TAIL_LINES', 50)
    core_api.read_namespaced_pod_log.return_value = 'line\n'

    run('kubectl', 'logs', 'default', 'web-abc/nginx')

    assert core_api.read_namespaced_pod_log.call_args.kwargs['tail_lines'] == 50


# Message

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

    kwargs = sent(ctx)
    assert kwargs['content'] == (
        '```'
        '🟩 INFO started\n'
        '🟦 debug: details\n'
        '🟧 Warning: slow\n'
        '🟥 ERROR failed\n'
        '🟦 TRACE x\n'
        '⬜ plain line\n'
        '```'
    )
    # Everything fits: no file
    assert 'file' not in kwargs


def test_too_long_keeps_latest_lines_and_attaches_full_log(run, ctx, core_api):
    lines = [f'line {i:04d} ' + 'x' * 90 for i in range(100)]
    core_api.read_namespaced_pod_log.return_value = '\x1b[31m' + '\n'.join(lines)

    run('kubectl', 'logs', 'default', 'web-abc/nginx')

    kwargs = sent(ctx)
    assert len(kwargs['content']) <= 2000
    assert lines[-1] in kwargs['content']
    assert lines[0] not in kwargs['content']
    # The file has every fetched line, ANSI sequences removed
    assert attached(kwargs) == ('web-abc-nginx.log', '\n'.join(lines))


def test_single_line_too_long_is_shortened(run, ctx, core_api):
    core_api.read_namespaced_pod_log.return_value = 'x' * 1999

    run('kubectl', 'logs', 'default', 'web-abc/nginx')

    kwargs = sent(ctx)
    content = kwargs['content']
    assert len(content) == 2000
    assert content.startswith('```⬜ xxx')
    assert content.endswith('x…\n```')
    assert attached(kwargs) == ('web-abc-nginx.log', 'x' * 1999)


@pytest.mark.parametrize('length', [1990, 1991, 1992, 1993, 1994, 2500])
def test_format_never_exceeds_discord_limit(length):
    """Around the exact budget: 3 chars added per line, 6 for the wrapper."""
    content, _ = logs.format_logs('x' * length)
    assert len(content) <= 2000


def test_format_exact_fit_is_complete():
    # '⬜ ' + line + '\n' + 6 for the wrapper == 2000
    content, complete = logs.format_logs('x' * (2000 - 6 - 3))
    assert len(content) == 2000
    assert complete


# Other answers

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
