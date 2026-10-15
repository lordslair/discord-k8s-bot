# -*- coding: utf8 -*-
#
# Autocomplete callbacks. Discord drops the request if it isn't answered within ~3s,
# and sends a new one on (almost) every keystroke, so:
# - the K8s calls run in a thread, never blocking the event loop;
# - choices are filtered by what the user typed, as Discord shows 25 at most.

import asyncio
import discord

from kubernetes import config, client
from loguru import logger

from subcommands.kubectl._kubeconfig import kubeconfig_file
from variables import K8S_NAMESPACES

# Discord's maximum number of autocomplete choices
MAX_CHOICES = 25


def _list_pods(namespace):
    config.load_kube_config(kubeconfig_file())
    return client.CoreV1Api().list_namespaced_pod(namespace)


def _list_namespaces():
    config.load_kube_config(kubeconfig_file())
    return client.CoreV1Api().list_namespace()


def _filter(ctx: discord.AutocompleteContext, choices):
    """Keep the choices containing the typed text (case-insensitive), 25 at most."""
    typed = (ctx.value or '').lower()
    return [
        c for c in choices
        if typed in c.name.lower() or typed in str(c.value).lower()
    ][:MAX_CHOICES]


async def k8s_list_namespaced_pod(ctx: discord.AutocompleteContext):
    try:
        pods = await asyncio.to_thread(_list_pods, ctx.options["namespace"])
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []

    return _filter(ctx, [discord.OptionChoice(pod.metadata.name) for pod in pods.items])


async def k8s_list_namespaced_containers(ctx: discord.AutocompleteContext):
    try:
        pods = await asyncio.to_thread(_list_pods, ctx.options["namespace"])
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []

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
    return _filter(ctx, db_list)


def split_container(value):
    """
    Split a '<pod>/<container>' value, as built by k8s_list_namespaced_containers.

    Raises ValueError for anything else (e.g. a value typed by the user).
    """
    pod_name, sep, container_name = value.partition('/')
    if not (pod_name and sep and container_name) or '/' in container_name:
        raise ValueError(f'expected <pod>/<container>, got {value!r}')
    return pod_name, container_name


async def k8s_list_namespaced_resources(ctx: discord.AutocompleteContext):
    if ctx.options["resource"] == 'pod':
        return await k8s_list_namespaced_pod(ctx)
    else:
        # Resource not chosen yet (or not supported): nothing to offer
        return []


async def k8s_list_namespace(ctx: discord.AutocompleteContext):
    try:
        namespaces = await asyncio.to_thread(_list_namespaces)
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []

    db_list = []
    for namespace in namespaces.items:
        if not K8S_NAMESPACES or namespace.metadata.name in K8S_NAMESPACES:
            db_list.append(discord.OptionChoice(namespace.metadata.name))
    return _filter(ctx, db_list)
