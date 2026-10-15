# -*- coding: utf8 -*-
"""/kubectl get: pods, deployments, pvc, services."""

import discord
import pytest

from helpers import (
    deployment,
    deployments,
    embed,
    pod,
    pods,
    pvc,
    pvcs,
    service,
    services,
)


# Pods

def test_pods(run, ctx, core_api):
    core_api.list_namespaced_pod.return_value = pods(
        pod('web-1', labels={'app': 'web'}, containers=[('nginx', True, 0)]),
        pod('api-1', labels={'app': 'api'}, containers=[('api', False, 3), ('proxy', True, 1)]),
    )

    run('kubectl', 'get', 'default', 'pods')

    core_api.list_namespaced_pod.assert_called_once_with('default')
    result = embed(ctx.interaction.edit_original_response)
    assert result.title == 'kubectl get pods [default]'
    assert result.colour == discord.Colour.green()
    assert result.description == (
        "`web-1`\n"
        "> 🟩  `nginx (0)`\n"
        "`api-1`\n"
        "> 🟥  `api (3)`\n"
        "> 🟩  `proxy (1)`\n"
    )


def test_pods_skips_job_pods(run, ctx, core_api):
    core_api.list_namespaced_pod.return_value = pods(
        pod('backup-123', labels={'job-name': 'backup'}),
        pod('web-1', labels={'app': 'web'}),
    )

    run('kubectl', 'get', 'default', 'pods')

    description = embed(ctx.interaction.edit_original_response).description
    assert 'web-1' in description
    assert 'backup-123' not in description


@pytest.mark.xfail(strict=True, raises=TypeError,
                   reason="Pod without labels: `'job-name' in None` raises TypeError")
def test_pods_without_labels(run, ctx, core_api):
    core_api.list_namespaced_pod.return_value = pods(pod('bare', labels=None))

    run('kubectl', 'get', 'default', 'pods')

    assert 'bare' in embed(ctx.interaction.edit_original_response).description


@pytest.mark.xfail(strict=True, raises=TypeError,
                   reason='Pod not started yet: container_statuses is None, not iterable')
def test_pods_not_started(run, ctx, core_api):
    core_api.list_namespaced_pod.return_value = pods(
        pod('pending', labels={'app': 'web'}, statuses=False),
    )

    run('kubectl', 'get', 'default', 'pods')

    assert 'pending' in embed(ctx.interaction.edit_original_response).description


# Deployments

def test_deployments(run, ctx, apps_api):
    apps_api.list_namespaced_deployment.return_value = deployments(
        deployment('web', replicas=2, available=2),
        deployment('api', replicas=3, available=1),
    )

    run('kubectl', 'get', 'default', 'deployments')

    apps_api.list_namespaced_deployment.assert_called_once_with('default')
    result = embed(ctx.interaction.edit_original_response)
    assert result.title == 'kubectl get deployment [default]'
    assert result.description == (
        "🟩  `web (2/2)`\n"
        "🟥  `api (1/3)`\n"
    )


def test_deployments_none(run, ctx, apps_api):
    apps_api.list_namespaced_deployment.return_value = deployments()

    run('kubectl', 'get', 'default', 'deployments')

    result = embed(ctx.respond)
    assert result.description == 'No deployment were found for this namespace'
    assert result.colour == discord.Colour.orange()


# PVC

def test_pvc(run, ctx, core_api):
    core_api.list_namespaced_persistent_volume_claim.return_value = pvcs(
        pvc('data', phase='Bound', storage='10Gi'),
        pvc('old', phase='Released', storage='1Gi'),
    )

    run('kubectl', 'get', 'default', 'pvc')

    result = embed(ctx.interaction.edit_original_response)
    assert result.title == 'kubectl get pvc [default]'
    assert result.description == (
        "🟩  `data (10Gi)`\n"
        "⬜  `old (1Gi)`\n"
    )


def test_pvc_none(run, ctx, core_api):
    core_api.list_namespaced_persistent_volume_claim.return_value = pvcs()

    run('kubectl', 'get', 'default', 'pvc')

    assert embed(ctx.respond).description == 'No pvc were found for this namespace'


@pytest.mark.xfail(strict=True, raises=TypeError,
                   reason='Pending PVC: status.capacity is None, not subscriptable')
def test_pvc_pending(run, ctx, core_api):
    core_api.list_namespaced_persistent_volume_claim.return_value = pvcs(
        pvc('new', phase='Pending', storage=None),
    )

    run('kubectl', 'get', 'default', 'pvc')

    assert 'new' in embed(ctx.interaction.edit_original_response).description


# Services

def test_services(run, ctx, core_api):
    core_api.list_namespaced_service.return_value = services(
        service('web', ports=[('http', 80, 8080), ('https', 443, 8443)]),
        service('lb', type='LoadBalancer', ports=[('http', 80, 80)], hostnames=['lb.example.com']),
    )

    run('kubectl', 'get', 'default', 'services')

    result = embed(ctx.interaction.edit_original_response)
    assert result.title == 'kubectl get services [default]'
    assert result.description == (
        "`web (ClusterIP)`\n"
        "> `10.0.0.1:80 -> http:8080`\n"
        "> `10.0.0.1:443 -> https:8443`\n"
        "`lb (LoadBalancer)`\n"
        "> `10.0.0.1:80 -> http:80`\n"
        "> `hostname: lb.example.com`\n"
    )


def test_services_none(run, ctx, core_api):
    core_api.list_namespaced_service.return_value = services()

    run('kubectl', 'get', 'default', 'services')

    assert embed(ctx.respond).description == 'No services were found for this namespace'


@pytest.mark.xfail(strict=True, raises=TypeError,
                   reason='LoadBalancer without address yet: ingress is None, not iterable')
def test_services_load_balancer_pending(run, ctx, core_api):
    core_api.list_namespaced_service.return_value = services(
        service('lb', type='LoadBalancer', hostnames=None),
    )

    run('kubectl', 'get', 'default', 'services')

    assert 'lb' in embed(ctx.interaction.edit_original_response).description


# Errors

@pytest.mark.parametrize('resource, api_name, method', [
    ('pods', 'core_api', 'list_namespaced_pod'),
    ('pvc', 'core_api', 'list_namespaced_persistent_volume_claim'),
    ('deployments', 'apps_api', 'list_namespaced_deployment'),
    ('services', 'core_api', 'list_namespaced_service'),
])
def test_api_error(request, run, ctx, resource, api_name, method):
    api = request.getfixturevalue(api_name)
    getattr(api, method).side_effect = Exception('boom')

    run('kubectl', 'get', 'default', resource)

    result = embed(ctx.respond)
    assert result.description == 'Command aborted: K8s Query KO'
    assert result.colour == discord.Colour.red()
