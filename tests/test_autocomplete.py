# -*- coding: utf8 -*-
"""Autocomplete callbacks: namespaces, pods and containers lists."""

import discord
import pytest

from unittest.mock import MagicMock

from helpers import module, namespaces, pod, pods

autocomplete = module('subcommands.kubectl._autocomplete')


def actx(**options):
    """Fake AutocompleteContext with the options already filled by the user."""
    ctx = MagicMock()
    ctx.options = options
    return ctx


def names(choices):
    assert all(isinstance(c, discord.OptionChoice) for c in choices)
    return [c.name for c in choices]


def values(choices):
    assert all(isinstance(c, discord.OptionChoice) for c in choices)
    return [c.value for c in choices]


# Namespaces

def test_namespaces_filtered_by_k8s_namespaces(monkeypatch, core_api):
    monkeypatch.setattr(autocomplete, 'K8S_NAMESPACES', ['default', 'prod'])
    core_api.list_namespace.return_value = namespaces('default', 'kube-system', 'prod')

    assert names(autocomplete.k8s_list_namespace(actx())) == ['default', 'prod']


def test_namespaces_all_when_k8s_namespaces_unset(monkeypatch, core_api):
    monkeypatch.setattr(autocomplete, 'K8S_NAMESPACES', None)
    core_api.list_namespace.return_value = namespaces('default', 'kube-system')

    assert names(autocomplete.k8s_list_namespace(actx())) == ['default', 'kube-system']


def test_namespaces_api_error(monkeypatch, core_api):
    monkeypatch.setattr(autocomplete, 'K8S_NAMESPACES', ['default'])
    core_api.list_namespace.side_effect = Exception('boom')

    assert autocomplete.k8s_list_namespace(actx()) == []


# Pods

def test_pods(core_api):
    core_api.list_namespaced_pod.return_value = pods(pod('web-1'), pod('web-2'))

    assert names(autocomplete.k8s_list_namespaced_pod(actx(namespace='default'))) == [
        'web-1', 'web-2',
    ]
    core_api.list_namespaced_pod.assert_called_once_with('default')


def test_pods_api_error(core_api):
    core_api.list_namespaced_pod.side_effect = Exception('boom')

    assert autocomplete.k8s_list_namespaced_pod(actx(namespace='default')) == []


def test_resources_pod(core_api):
    core_api.list_namespaced_pod.return_value = pods(pod('web-1'))

    choices = autocomplete.k8s_list_namespaced_resources(
        actx(namespace='default', resource='pod'),
    )
    assert names(choices) == ['web-1']


def test_resources_other():
    assert autocomplete.k8s_list_namespaced_resources(actx(resource='service')) is None


# Containers: shown as <label>/<container>, value is always <pod>/<container>

def test_containers_by_label(core_api):
    core_api.list_namespaced_pod.return_value = pods(
        pod('web-abc', labels={'name': 'web'}, containers=[('nginx', True, 0)]),
        pod('api-def', labels={'app': 'api'}, containers=[('api', True, 0), ('proxy', True, 0)]),
        pod('db-ghi', labels={'tier': 'db'}, containers=[('postgres', True, 0)]),
    )

    choices = autocomplete.k8s_list_namespaced_containers(actx(namespace='default'))

    assert names(choices) == ['web/nginx', 'api/api', 'api/proxy', 'db-ghi/postgres']
    assert values(choices) == [
        'web-abc/nginx', 'api-def/api', 'api-def/proxy', 'db-ghi/postgres',
    ]


def test_containers_pod_without_labels(core_api):
    core_api.list_namespaced_pod.return_value = pods(
        pod('bare', labels=None, containers=[('app', True, 0)]),
    )

    choices = autocomplete.k8s_list_namespaced_containers(actx(namespace='default'))
    assert values(choices) == ['bare/app']


def test_containers_api_error(core_api):
    core_api.list_namespaced_pod.side_effect = Exception('boom')

    assert autocomplete.k8s_list_namespaced_containers(actx(namespace='default')) == []


# '<pod>/<container>' values

def test_split_container():
    assert autocomplete.split_container('web-abc/nginx') == ('web-abc', 'nginx')


@pytest.mark.parametrize('value', ['nginx', 'web-abc/', '/nginx', 'a/b/c', ''])
def test_split_container_invalid(value):
    with pytest.raises(ValueError):
        autocomplete.split_container(value)
