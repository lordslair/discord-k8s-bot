# -*- coding: utf8 -*-
"""/diskube settings and /kubectl apply, config, delete, exec."""

import discord
import pytest

from unittest.mock import MagicMock

from helpers import embed, module


# /diskube settings

def test_settings(run, ctx, monkeypatch):
    monkeypatch.setenv('KUBECONFIG_FILE', '/tmp/kubeconfig.yaml')
    monkeypatch.setenv('DISCORD_GUILD', '1234')

    run('diskube', 'settings')

    result = embed(ctx.respond)
    assert result.title == 'diskube settings'
    assert '> KUBECONFIG_FILE: `/tmp/kubeconfig.yaml`' in result.description
    assert '> DISCORD_GUILD: `1234`' in result.description


# /kubectl apply

def test_apply_not_implemented(run, ctx):
    run('kubectl', 'apply', 'default')

    result = embed(ctx.respond)
    assert result.title == 'kubectl apply [default]'
    assert result.description == 'Not implemented yet.'


# /kubectl config

KUBECONFIG = """
apiVersion: v1
clusters:
- name: my-cluster
  cluster:
    server: https://k8s.example.com:6443
"""


def test_config_show(run, ctx, monkeypatch, tmp_path):
    kubeconfig = tmp_path / 'kubeconfig.yaml'
    kubeconfig.write_text(KUBECONFIG)
    monkeypatch.setenv('KUBECONFIG_FILE', str(kubeconfig))

    run('kubectl', 'config', 'show')

    result = embed(ctx.interaction.edit_original_response)
    assert result.colour == discord.Colour.green()
    assert '> Name: my-cluster' in result.description
    assert '> Server: https://k8s.example.com:6443' in result.description


def test_config_invalid_yaml(run, ctx, monkeypatch, tmp_path):
    kubeconfig = tmp_path / 'kubeconfig.yaml'
    kubeconfig.write_text('clusters: []\n')
    monkeypatch.setenv('KUBECONFIG_FILE', str(kubeconfig))

    run('kubectl', 'config', 'show')

    result = embed(ctx.interaction.edit_original_response)
    assert result.description == 'Unable to load YAML file.'
    assert result.colour == discord.Colour.red()


def test_config_file_not_found(run, ctx, monkeypatch, tmp_path):
    monkeypatch.setenv('KUBECONFIG_FILE', str(tmp_path / 'missing.yaml'))

    run('kubectl', 'config', 'show')

    result = embed(ctx.interaction.edit_original_response)
    assert result.description.startswith('YAML file not found')
    assert result.colour == discord.Colour.red()


@pytest.mark.xfail(strict=True, reason='Missing f prefix: shows a literal {KUBECONFIG_FILE}')
def test_config_file_not_found_shows_path(run, ctx, monkeypatch, tmp_path):
    missing = str(tmp_path / 'missing.yaml')
    monkeypatch.setenv('KUBECONFIG_FILE', missing)

    run('kubectl', 'config', 'show')

    assert missing in embed(ctx.interaction.edit_original_response).description


# /kubectl delete

def test_delete_pod(run, ctx, core_api):
    run('kubectl', 'delete', 'default', 'pod', 'web-abc')

    core_api.delete_namespaced_pod.assert_called_once_with('web-abc', 'default')
    result = embed(ctx.interaction.edit_original_response)
    assert result.title == 'kubectl delete pod [default]'
    assert result.description == 'The pod `web-abc` was terminated.'


def test_delete_api_error(run, ctx, core_api):
    core_api.delete_namespaced_pod.side_effect = Exception('boom')

    run('kubectl', 'delete', 'default', 'pod', 'web-abc')

    assert embed(ctx.respond).description == 'Command aborted: K8s Query KO'
    ctx.interaction.edit_original_response.assert_not_called()


# /kubectl exec

@pytest.fixture
def stream(monkeypatch, core_api):
    stream = MagicMock(return_value='total 0\n')
    monkeypatch.setattr(module('subcommands.kubectl.exec'), 'stream', stream)
    return stream


def test_exec(run, ctx, core_api, stream):
    run('kubectl', 'exec', 'default', 'web-abc/nginx', 'ls -l /tmp')

    stream.assert_called_once_with(
        core_api.connect_get_namespaced_pod_exec,
        'web-abc',
        'default',
        container='nginx',
        command=['ls', '-l', '/tmp'],
        stderr=True, stdin=False,
        stdout=True, tty=False,
    )
    result = embed(ctx.interaction.edit_original_response)
    assert result.title == 'K8s exec'
    assert result.description == '> `ls -l /tmp`\n```total 0\n```'


def test_exec_error(run, ctx, stream):
    stream.side_effect = Exception('boom')

    run('kubectl', 'exec', 'default', 'web-abc/nginx', 'ls')

    result = embed(ctx.respond)
    assert result.description == 'K8s exec KO [boom]'
    assert result.colour == discord.Colour.red()
