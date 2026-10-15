# -*- coding: utf8 -*-
"""/diskube settings and /kubectl apply, config, delete, exec."""

import threading

import discord
import kubernetes
import pytest

from unittest.mock import MagicMock

from helpers import deployments, embed, module, pods, pvcs, services


# /diskube settings

def test_settings(run, ctx, monkeypatch):
    monkeypatch.setenv('KUBECONFIG_FILE', '/tmp/kubeconfig.yaml')
    monkeypatch.setenv('DISCORD_GUILD', '1234')

    run('diskube', 'settings')

    result = embed(ctx.respond)
    assert result.title == 'diskube settings'
    assert '> KUBECONFIG_FILE: `/tmp/kubeconfig.yaml`' in result.description
    assert '> DISCORD_GUILD: `1234`' in result.description


def test_settings_version(run, ctx, monkeypatch):
    monkeypatch.setenv('DISKUBE_VERSION', '1.2.3')
    monkeypatch.setenv('DISKUBE_COMMIT', '0123456789abcdef0123456789abcdef01234567')

    run('diskube', 'settings')

    assert embed(ctx.respond).description.startswith(
        "Version:\n"
        "> Release: `1.2.3`\n"
        "> Commit: `0123456`\n"
    )


def test_settings_version_local_build(run, ctx, monkeypatch):
    monkeypatch.delenv('DISKUBE_VERSION', raising=False)
    monkeypatch.delenv('DISKUBE_COMMIT', raising=False)

    run('diskube', 'settings')

    assert embed(ctx.respond).description.startswith(
        "Version:\n"
        "> Release: `dev`\n"
        "> Commit: `unknown`\n"
    )


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


def test_config_file_not_found_shows_path(run, ctx, monkeypatch, tmp_path):
    missing = str(tmp_path / 'missing.yaml')
    monkeypatch.setenv('KUBECONFIG_FILE', missing)

    run('kubectl', 'config', 'show')

    assert embed(ctx.interaction.edit_original_response).description == (
        f'YAML file not found (Should be there: `{missing}`).'
    )


# /kubectl delete

def test_delete_pod(run, ctx, core_api):
    run('kubectl', 'delete', 'default', 'pod', 'web-abc')

    core_api.delete_namespaced_pod.assert_called_once_with('web-abc', 'default')
    result = embed(ctx.interaction.edit_original_response)
    assert result.title == 'kubectl delete pod [default]'
    assert result.description == 'The pod `web-abc` was terminated.'


def test_delete_forgets_cached_pods(run, core_api):
    """The deleted pod disappears from autocomplete at once, not after the cache delay."""
    cache = module('subcommands.kubectl._autocomplete')._pods_cache
    cache.update({'default': 'pods list', 'prod': 'pods list'})

    run('kubectl', 'delete', 'default', 'pod', 'web-abc')

    assert cache == {'prod': 'pods list'}


def test_delete_error_keeps_cached_pods(run, core_api):
    cache = module('subcommands.kubectl._autocomplete')._pods_cache
    cache.update({'default': 'pods list'})
    core_api.delete_namespaced_pod.side_effect = Exception('boom')

    run('kubectl', 'delete', 'default', 'pod', 'web-abc')

    assert cache == {'default': 'pods list'}


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


@pytest.mark.parametrize('name, args', [
    ('exec', ('default', 'nginx', 'ls')),
    ('logs', ('default', 'nginx')),
])
def test_invalid_container(run, ctx, core_api, name, args):
    """A value typed by the user instead of picked from the list."""
    run('kubectl', name, *args)

    result = embed(ctx.respond)
    assert result.description == 'Invalid container `nginx`: pick one from the list.'
    assert result.colour == discord.Colour.red()
    core_api.read_namespaced_pod_log.assert_not_called()
    core_api.connect_get_namespaced_pod_exec.assert_not_called()


# Kubeconfig loading, shared by every command that queries the cluster

COMMANDS = [
    ('apply', ('default',)),
    ('delete', ('default', 'pod', 'web-abc')),
    ('exec', ('default', 'web-abc/nginx', 'ls')),
    ('get', ('default', 'pods')),
    ('logs', ('default', 'web-abc/nginx')),
]


@pytest.mark.parametrize('name, args', COMMANDS)
def test_kubeconfig_error_aborts(monkeypatch, run, ctx, core_api, name, args):
    monkeypatch.setattr(
        kubernetes.config, 'load_kube_config', MagicMock(side_effect=Exception('boom')),
    )

    run('kubectl', name, *args)

    result = embed(ctx.respond)
    assert result.description == 'Command aborted: K8s config KO'
    assert result.colour == discord.Colour.red()
    # Stopped before any query or answer
    assert core_api.method_calls == []
    ctx.interaction.edit_original_response.assert_not_called()


@pytest.mark.parametrize('name, args', COMMANDS)
def test_kubeconfig_file_from_variable(monkeypatch, run, core_api, name, args):
    monkeypatch.setenv('KUBECONFIG_FILE', '/tmp/kubeconfig.yaml')
    core_api.read_namespaced_pod_log.return_value = ''  # logs needs a str

    run('kubectl', name, *args)

    kubernetes.config.load_kube_config.assert_called_once_with('/tmp/kubeconfig.yaml')


@pytest.mark.parametrize('name, args', COMMANDS)
def test_kubeconfig_file_default(monkeypatch, run, core_api, name, args):
    monkeypatch.delenv('KUBECONFIG_FILE', raising=False)
    core_api.read_namespaced_pod_log.return_value = ''  # logs needs a str

    run('kubectl', name, *args)

    kubernetes.config.load_kube_config.assert_called_once_with('/etc/k8s/kubeconfig.yaml')


# Never block the event loop (and every other interaction): blocking calls run in a thread

def recorder(threads, result=None):
    def _record(*args, **kwargs):
        threads.append(threading.current_thread())
        return result
    return _record


@pytest.mark.parametrize('name, args', COMMANDS)
def test_kubeconfig_loaded_in_a_thread(run, core_api, name, args):
    core_api.read_namespaced_pod_log.return_value = ''  # logs needs a str
    threads = []
    kubernetes.config.load_kube_config.side_effect = recorder(threads)

    run('kubectl', name, *args)

    assert threads and threads[0] is not threading.main_thread()


@pytest.mark.parametrize('name, args, api_name, method, result', [
    ('get', ('default', 'pods'), 'core_api', 'list_namespaced_pod', pods()),
    ('get', ('default', 'pvc'), 'core_api', 'list_namespaced_persistent_volume_claim', pvcs()),
    ('get', ('default', 'deployments'), 'apps_api', 'list_namespaced_deployment', deployments()),
    ('get', ('default', 'services'), 'core_api', 'list_namespaced_service', services()),
    ('delete', ('default', 'pod', 'web-abc'), 'core_api', 'delete_namespaced_pod', None),
    ('logs', ('default', 'web-abc/nginx'), 'core_api', 'read_namespaced_pod_log', ''),
])
def test_k8s_query_in_a_thread(request, run, name, args, api_name, method, result):
    threads = []
    getattr(request.getfixturevalue(api_name), method).side_effect = recorder(threads, result)

    run('kubectl', name, *args)

    assert threads and threads[0] is not threading.main_thread()


def test_exec_in_a_thread(run, stream):
    threads = []
    stream.side_effect = recorder(threads, 'output')

    run('kubectl', 'exec', 'default', 'web-abc/nginx', 'ls')

    assert threads and threads[0] is not threading.main_thread()
