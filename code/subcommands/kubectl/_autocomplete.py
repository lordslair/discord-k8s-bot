# -*- coding: utf8 -*-

import discord

from kubernetes import config, client
from loguru import logger

from variables import K8S_NAMESPACES


def k8s_list_namespaced_pod(ctx: discord.AutocompleteContext):
    try:
        config.load_kube_config("/etc/k8s/kubeconfig.yaml")
        pods = client.CoreV1Api().list_namespaced_pod(ctx.options["namespace"])
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []
    else:
        db_list = []
        for pod in pods.items:
            db_list.append(discord.OptionChoice(pod.metadata.name))
        return db_list


def k8s_list_namespaced_resources(ctx: discord.AutocompleteContext):
    if ctx.options["resource"] == 'pod':
        return k8s_list_namespaced_pod(ctx)
    else:
        return None


def k8s_list_namespace(ctx: discord.AutocompleteContext):
    try:
        config.load_kube_config("/etc/k8s/kubeconfig.yaml")
        namespaces = client.CoreV1Api().list_namespace()
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []
    else:
        db_list = []
        if len(K8S_NAMESPACES) > 0:
            for namespace in namespaces.items:
                if namespace.metadata.name in K8S_NAMESPACES:
                    db_list.append(discord.OptionChoice(namespace.metadata.name))
        else:
            for namespace in namespaces.items:
                db_list.append(discord.OptionChoice(namespace.metadata.name))
        return db_list


def k8s_list_pod_containers(ctx: discord.AutocompleteContext):
    try:
        config.load_kube_config("/etc/k8s/kubeconfig.yaml")
        pod = client.CoreV1Api().read_namespaced_pod(
            namespace=ctx.options["namespace"],
            name=ctx.options["resource_name"],
            )
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []
    else:
        db_list = []
        for container in pod.spec.containers:
            db_list.append(discord.OptionChoice(container.name))
        return db_list
