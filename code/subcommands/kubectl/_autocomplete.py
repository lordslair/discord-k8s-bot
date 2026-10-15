# -*- coding: utf8 -*-

import discord

from kubernetes import config, client
from loguru import logger

from subcommands.kubectl._kubeconfig import kubeconfig_file
from variables import K8S_NAMESPACES


def k8s_list_namespaced_pod(ctx: discord.AutocompleteContext):
    try:
        config.load_kube_config(kubeconfig_file())
        pods = client.CoreV1Api().list_namespaced_pod(ctx.options["namespace"])
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []
    else:
        db_list = []
        for pod in pods.items:
            db_list.append(discord.OptionChoice(pod.metadata.name))
        return db_list


def k8s_list_namespaced_containers(ctx: discord.AutocompleteContext):
    try:
        config.load_kube_config(kubeconfig_file())
        pods = client.CoreV1Api().list_namespaced_pod(ctx.options["namespace"])
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []
    else:
        db_list = []
        for pod in pods.items:
            # labels is None on a pod without any
            labels = pod.metadata.labels or {}
            for container in pod.spec.containers:
                if 'name' in labels:
                    db_list.append(
                        discord.OptionChoice(
                            f"{labels['name']}/{container.name}",
                            value=f'{pod.metadata.name}/{container.name}'
                            )
                      )
                elif 'app' in labels:
                    db_list.append(
                        discord.OptionChoice(
                            f"{labels['app']}/{container.name}",
                            value=f'{pod.metadata.name}/{container.name}'
                            )
                      )
                else:
                    db_list.append(
                        discord.OptionChoice(f'{pod.metadata.name}/{container.name}')
                      )
        return db_list


def split_container(value):
    """
    Split a '<pod>/<container>' value, as built by k8s_list_namespaced_containers.

    Raises ValueError for anything else (e.g. a value typed by the user).
    """
    pod_name, sep, container_name = value.partition('/')
    if not (pod_name and sep and container_name) or '/' in container_name:
        raise ValueError(f'expected <pod>/<container>, got {value!r}')
    return pod_name, container_name


def k8s_list_namespaced_resources(ctx: discord.AutocompleteContext):
    if ctx.options["resource"] == 'pod':
        return k8s_list_namespaced_pod(ctx)
    else:
        return None


def k8s_list_namespace(ctx: discord.AutocompleteContext):
    try:
        config.load_kube_config(kubeconfig_file())
        namespaces = client.CoreV1Api().list_namespace()
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []
    else:
        db_list = []
        if K8S_NAMESPACES:
            for namespace in namespaces.items:
                if namespace.metadata.name in K8S_NAMESPACES:
                    db_list.append(discord.OptionChoice(namespace.metadata.name))
        else:
            for namespace in namespaces.items:
                db_list.append(discord.OptionChoice(namespace.metadata.name))
        return db_list
