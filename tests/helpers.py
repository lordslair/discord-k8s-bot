# -*- coding: utf8 -*-
"""Helpers to build Kubernetes objects and read what was sent to Discord."""

import importlib

from kubernetes.client import (
    V1Container,
    V1ContainerStatus,
    V1Deployment,
    V1DeploymentList,
    V1DeploymentSpec,
    V1DeploymentStatus,
    V1LabelSelector,
    V1LoadBalancerIngress,
    V1LoadBalancerStatus,
    V1Namespace,
    V1NamespaceList,
    V1ObjectMeta,
    V1PersistentVolumeClaim,
    V1PersistentVolumeClaimList,
    V1PersistentVolumeClaimStatus,
    V1Pod,
    V1PodList,
    V1PodSpec,
    V1PodStatus,
    V1PodTemplateSpec,
    V1Service,
    V1ServiceList,
    V1ServicePort,
    V1ServiceSpec,
    V1ServiceStatus,
)


def module(name):
    """
    Return a subcommand module, e.g. module('subcommands.kubectl.exec').

    `import subcommands.kubectl.exec` would give the function of the same name,
    re-exported by the package __init__, not the module.
    """
    return importlib.import_module(name)


def embed(mock):
    """Embed passed to the last call of respond() or edit_original_response()."""
    assert mock.call_args is not None, 'no answer was sent this way'
    return mock.call_args.kwargs['embed']


# Kubernetes objects (real client models, so a wrong attribute name fails)

def namespaces(*names):
    return V1NamespaceList(items=[V1Namespace(metadata=V1ObjectMeta(name=n)) for n in names])


def pod(name, labels=None, containers=(('app', True, 0),), statuses=True):
    """containers: (name, ready, restart_count). statuses=False: pod not started yet."""
    return V1Pod(
        metadata=V1ObjectMeta(name=name, labels=labels),
        spec=V1PodSpec(containers=[V1Container(name=c[0]) for c in containers]),
        status=V1PodStatus(
            container_statuses=[
                V1ContainerStatus(
                    name=c[0], ready=c[1], restart_count=c[2], image='img', image_id='id',
                )
                for c in containers
            ] if statuses else None,
        ),
    )


def pods(*items):
    return V1PodList(items=list(items))


def deployment(name, replicas, available):
    return V1Deployment(
        metadata=V1ObjectMeta(name=name),
        spec=V1DeploymentSpec(
            replicas=replicas,
            selector=V1LabelSelector(),
            template=V1PodTemplateSpec(),
        ),
        status=V1DeploymentStatus(available_replicas=available),
    )


def deployments(*items):
    return V1DeploymentList(items=list(items))


def pvc(name, phase='Bound', storage='1Gi'):
    return V1PersistentVolumeClaim(
        metadata=V1ObjectMeta(name=name),
        status=V1PersistentVolumeClaimStatus(
            phase=phase,
            capacity={'storage': storage} if storage else None,
        ),
    )


def pvcs(*items):
    return V1PersistentVolumeClaimList(items=list(items))


def service(name, type='ClusterIP', ports=(('http', 80, 8080),), hostnames=None, ips=None):
    """
    ports: (name, port, target_port).
    hostnames / ips: LoadBalancer ingress addresses, both None while pending.
    """
    if hostnames is None and ips is None:
        ingress = None
    else:
        ingress = (
            [V1LoadBalancerIngress(hostname=h) for h in hostnames or []]
            + [V1LoadBalancerIngress(ip=i) for i in ips or []]
        )
    return V1Service(
        metadata=V1ObjectMeta(name=name),
        spec=V1ServiceSpec(
            type=type,
            cluster_ip='10.0.0.1',
            ports=[V1ServicePort(name=p[0], port=p[1], target_port=p[2]) for p in ports],
        ),
        status=V1ServiceStatus(
            load_balancer=V1LoadBalancerStatus(ingress=ingress),
        ),
    )


def services(*items):
    return V1ServiceList(items=list(items))
