# -*- coding: utf8 -*-
"""Autocomplete callbacks: namespaces, pods and containers lists."""

import asyncio
import threading
import time

import discord
import pytest

from unittest.mock import AsyncMock, MagicMock

from helpers import module, namespaces, pod, pods

autocomplete = module('subcommands.kubectl._autocomplete')


def actx(typed='', **options):
    """Fake AutocompleteContext: options already filled, and what the user typed so far."""
    ctx = MagicMock()
    ctx.options = options
    ctx.value = typed
    return ctx


def complete(callback, typed='', **options):
    """Run one autocomplete callback, as py-cord does."""
    return asyncio.run(callback(actx(typed, **options)))


def names(choices):
    assert all(isinstance(c, discord.OptionChoice) for c in choices)
    return [c.name for c in choices]


def values(choices):
    assert all(isinstance(c, discord.OptionChoice) for c in choices)
    return [c.value for c in choices]


# Namespaces

def test_namespaces_from_k8s_namespaces_without_cluster_call(monkeypatch, core_api):
    """Instant, and works without the right to list namespaces cluster-wide."""
    monkeypatch.setattr(autocomplete, 'K8S_NAMESPACES', ['prod', 'default'])
    core_api.list_namespace.side_effect = Exception('403 Forbidden')

    assert names(complete(autocomplete.k8s_list_namespace)) == ['prod', 'default']
    core_api.list_namespace.assert_not_called()


def test_namespaces_from_k8s_namespaces_filtered_by_typed_text(monkeypatch):
    monkeypatch.setattr(autocomplete, 'K8S_NAMESPACES', ['default', 'prod', 'preprod'])

    assert names(complete(autocomplete.k8s_list_namespace, typed='PROD')) == ['prod', 'preprod']


def test_namespaces_all_when_k8s_namespaces_unset(monkeypatch, core_api):
    monkeypatch.setattr(autocomplete, 'K8S_NAMESPACES', None)
    core_api.list_namespace.return_value = namespaces('default', 'kube-system')

    assert names(complete(autocomplete.k8s_list_namespace)) == ['default', 'kube-system']


def test_namespaces_api_error(monkeypatch, core_api):
    monkeypatch.setattr(autocomplete, 'K8S_NAMESPACES', None)
    core_api.list_namespace.side_effect = Exception('boom')

    assert complete(autocomplete.k8s_list_namespace) == []


# Pods

def test_pods(core_api):
    core_api.list_namespaced_pod.return_value = pods(pod('web-1'), pod('web-2'))

    assert names(complete(autocomplete.k8s_list_namespaced_pod, namespace='default')) == [
        'web-1', 'web-2',
    ]
    core_api.list_namespaced_pod.assert_called_once_with('default')


def test_pods_api_error(core_api):
    core_api.list_namespaced_pod.side_effect = Exception('boom')

    assert complete(autocomplete.k8s_list_namespaced_pod, namespace='default') == []


def test_resources_pod(core_api):
    core_api.list_namespaced_pod.return_value = pods(pod('web-1'))

    choices = complete(
        autocomplete.k8s_list_namespaced_resources, namespace='default', resource='pod',
    )
    assert names(choices) == ['web-1']


@pytest.mark.parametrize('resource', ['service', None])
def test_resources_other_or_not_chosen_yet(resource):
    """Must be a list: py-cord iterates over the result."""
    assert complete(autocomplete.k8s_list_namespaced_resources, resource=resource) == []


# Containers: shown as <label>/<container>, value is always <pod>/<container>

def test_containers_by_label(core_api):
    core_api.list_namespaced_pod.return_value = pods(
        pod('web-abc', labels={'name': 'web'}, containers=[('nginx', True, 0)]),
        pod('api-def', labels={'app': 'api'}, containers=[('api', True, 0), ('proxy', True, 0)]),
        pod('db-ghi', labels={'tier': 'db'}, containers=[('postgres', True, 0)]),
    )

    choices = complete(autocomplete.k8s_list_namespaced_containers, namespace='default')

    assert names(choices) == ['web/nginx', 'api/api', 'api/proxy', 'db-ghi/postgres']
    assert values(choices) == [
        'web-abc/nginx', 'api-def/api', 'api-def/proxy', 'db-ghi/postgres',
    ]


def test_containers_pod_without_labels(core_api):
    core_api.list_namespaced_pod.return_value = pods(
        pod('bare', labels=None, containers=[('app', True, 0)]),
    )

    choices = complete(autocomplete.k8s_list_namespaced_containers, namespace='default')
    assert values(choices) == ['bare/app']


def test_containers_api_error(core_api):
    core_api.list_namespaced_pod.side_effect = Exception('boom')

    assert complete(autocomplete.k8s_list_namespaced_containers, namespace='default') == []


# What the user typed: Discord shows 25 choices at most

def test_typed_text_filters_choices(core_api):
    core_api.list_namespaced_pod.return_value = pods(pod('web-1'), pod('api-1'), pod('WEB-2'))

    choices = complete(autocomplete.k8s_list_namespaced_pod, typed='web', namespace='default')
    assert names(choices) == ['web-1', 'WEB-2']


def test_typed_text_reaches_choices_beyond_25(core_api):
    core_api.list_namespaced_pod.return_value = pods(*[pod(f'pod-{i:02d}') for i in range(40)])

    assert len(complete(autocomplete.k8s_list_namespaced_pod, namespace='default')) == 25
    choices = complete(autocomplete.k8s_list_namespaced_pod, typed='pod-3', namespace='default')
    assert names(choices) == [f'pod-3{i}' for i in range(10)]


def test_typed_text_matches_container_value(core_api):
    """Shown as <label>/<container>, but the pod name typed must match too."""
    core_api.list_namespaced_pod.return_value = pods(
        pod('web-abc', labels={'app': 'web'}, containers=[('nginx', True, 0)]),
        pod('api-def', labels={'app': 'api'}, containers=[('api', True, 0)]),
    )

    choices = complete(
        autocomplete.k8s_list_namespaced_containers, typed='abc', namespace='default',
    )
    assert values(choices) == ['web-abc/nginx']


# Pod lists cache: one cluster call per burst of keystrokes

def requests(*calls):
    """Run several autocomplete requests one after the other, in one event loop (as the bot)."""
    async def _run():
        return [await callback(actx(**options)) for callback, options in calls]
    return asyncio.run(_run())


@pytest.fixture
def clock(monkeypatch):
    """Controllable time for the cache: clock[0] += 5 moves 5 seconds forward."""
    now = [1000.0]
    monkeypatch.setattr(autocomplete, '_now', lambda: now[0])
    return now


def test_pods_cache_shared_by_pods_and_containers(core_api):
    core_api.list_namespaced_pod.return_value = pods(pod('web-1'))

    requests(
        (autocomplete.k8s_list_namespaced_pod, {'namespace': 'default', 'typed': 'w'}),
        (autocomplete.k8s_list_namespaced_pod, {'namespace': 'default', 'typed': 'we'}),
        (autocomplete.k8s_list_namespaced_containers, {'namespace': 'default'}),
    )

    core_api.list_namespaced_pod.assert_called_once_with('default')


def test_pods_cache_per_namespace(core_api):
    core_api.list_namespaced_pod.return_value = pods(pod('web-1'))

    requests(
        (autocomplete.k8s_list_namespaced_pod, {'namespace': 'default'}),
        (autocomplete.k8s_list_namespaced_pod, {'namespace': 'prod'}),
        (autocomplete.k8s_list_namespaced_pod, {'namespace': 'default'}),
    )

    assert [c.args for c in core_api.list_namespaced_pod.call_args_list] == [
        ('default',), ('prod',),
    ]


def test_pods_cache_expires(core_api, clock):
    core_api.list_namespaced_pod.return_value = pods(pod('web-1'))
    pod_request = (autocomplete.k8s_list_namespaced_pod, {'namespace': 'default'})

    async def _run():
        await pod_request[0](actx(**pod_request[1]))
        clock[0] += autocomplete.PODS_CACHE_TTL - 0.1  # still fresh
        await pod_request[0](actx(**pod_request[1]))
        clock[0] += 0.1                                # expired
        await pod_request[0](actx(**pod_request[1]))
    asyncio.run(_run())

    assert core_api.list_namespaced_pod.call_count == 2


def test_pods_cache_ignores_errors(core_api):
    core_api.list_namespaced_pod.side_effect = [Exception('boom'), pods(pod('web-1'))]

    first, second = requests(
        (autocomplete.k8s_list_namespaced_pod, {'namespace': 'default'}),
        (autocomplete.k8s_list_namespaced_pod, {'namespace': 'default'}),
    )

    assert first == []
    assert names(second) == ['web-1']
    assert core_api.list_namespaced_pod.call_count == 2


def test_pods_cache_concurrent_requests_share_one_call(core_api):
    """Keystrokes arriving while the cluster is still answering wait for the same call."""
    def slow_list(namespace):
        time.sleep(0.2)
        return pods(pod('web-1'))
    core_api.list_namespaced_pod.side_effect = slow_list

    async def _run():
        return await asyncio.gather(*[
            autocomplete.k8s_list_namespaced_pod(actx(namespace='default', typed=t))
            for t in ('w', 'we', 'web')
        ])
    results = asyncio.run(_run())

    assert [names(r) for r in results] == [['web-1']] * 3
    core_api.list_namespaced_pod.assert_called_once_with('default')


# Never block the event loop: K8s calls run in another thread

@pytest.mark.parametrize('callback, method', [
    ('k8s_list_namespace', 'list_namespace'),
    ('k8s_list_namespaced_pod', 'list_namespaced_pod'),
    ('k8s_list_namespaced_containers', 'list_namespaced_pod'),
])
def test_k8s_calls_run_in_a_thread(monkeypatch, core_api, callback, method):
    monkeypatch.setattr(autocomplete, 'K8S_NAMESPACES', None)
    threads = []

    def record(*args):
        threads.append(threading.current_thread())
        return pods() if method == 'list_namespaced_pod' else namespaces()
    getattr(core_api, method).side_effect = record

    complete(getattr(autocomplete, callback), namespace='default')

    assert threads and threads[0] is not threading.main_thread()


# '<pod>/<container>' values

def test_split_container():
    assert autocomplete.split_container('web-abc/nginx') == ('web-abc', 'nginx')


@pytest.mark.parametrize('value', ['nginx', 'web-abc/', '/nginx', 'a/b/c', ''])
def test_split_container_invalid(value):
    with pytest.raises(ValueError):
        autocomplete.split_container(value)


# Through py-cord itself, as when Discord sends an autocomplete interaction

def test_through_py_cord(command, loop, core_api):
    core_api.list_namespaced_pod.return_value = pods(
        pod('web-abc', labels={'app': 'web'}, containers=[('nginx', True, 0)]),
        pod('api-def', labels={'app': 'api'}, containers=[('api', True, 0)]),
    )
    ctx = MagicMock()
    ctx.cog = None
    ctx.interaction.data = {'options': [
        {'name': 'namespace', 'value': 'default'},
        {'name': 'container', 'value': 'we', 'focused': True},
    ]}
    ctx.interaction.response.send_autocomplete_result = AsyncMock()

    loop.run_until_complete(command('kubectl', 'logs').invoke_autocomplete_callback(ctx))

    choices = ctx.interaction.response.send_autocomplete_result.call_args.kwargs['choices']
    assert [(c.name, c.value) for c in choices] == [('web/nginx', 'web-abc/nginx')]
