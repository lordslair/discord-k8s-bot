# -*- coding: utf8 -*-
#
# Autocomplete callbacks. Discord drops the request if it isn't answered within ~3s,
# and sends a new one on (almost) every keystroke, so:
# - the K8s calls run in a thread, never blocking the event loop;
# - choices are filtered by what the user typed, as Discord shows 25 at most;
# - pod lists are cached a few seconds.

import asyncio
import discord
import time

from kubernetes import config, client
from loguru import logger

from subcommands.kubectl._kubeconfig import kubeconfig_file
from variables import K8S_NAMESPACES

# Discord's maximum number of autocomplete choices
MAX_CHOICES = 25

# Pod lists are reused for a few seconds, per namespace: a burst of keystrokes
# makes one cluster call. Commands always query the cluster, never this cache.
PODS_CACHE_TTL = 5  # seconds
_pods_cache = {}  # namespace -> (time, task listing its pods)
_now = time.monotonic


def _list_pods(namespace):
    config.load_kube_config(kubeconfig_file())
    return client.CoreV1Api().list_namespaced_pod(namespace)


async def _cached_pods(namespace):
    cached = _pods_cache.get(namespace)
    if cached is None or _now() - cached[0] >= PODS_CACHE_TTL:
        # The task (not its result) is cached: requests arriving while the cluster
        # is still answering wait for this same call instead of starting new ones
        task = asyncio.ensure_future(asyncio.to_thread(_list_pods, namespace))
        cached = (_now(), task)
        _pods_cache[namespace] = cached

    try:
        # shield: a cancelled request must not cancel the call others are waiting for
        return await asyncio.shield(cached[1])
    except Exception:
        # Errors are not cached: the next request tries again
        if _pods_cache.get(namespace) is cached:
            del _pods_cache[namespace]
        raise


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


def forget_pods(namespace):
    """Drop a namespace's cached pod list, e.g. once a pod was deleted."""
    _pods_cache.pop(namespace, None)


async def k8s_list_namespaced_pod(ctx: discord.AutocompleteContext):
    try:
        pods = await _cached_pods(ctx.options["namespace"])
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []

    return _filter(ctx, [discord.OptionChoice(pod.metadata.name) for pod in pods.items])


async def k8s_list_namespaced_containers(ctx: discord.AutocompleteContext):
    try:
        pods = await _cached_pods(ctx.options["namespace"])
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
    # Namespaces given in K8S_NAMESPACES: offered as is, without querying the cluster.
    # Instant, and works when the bot isn't allowed to list namespaces cluster-wide
    if K8S_NAMESPACES:
        return _filter(ctx, [discord.OptionChoice(n) for n in K8S_NAMESPACES])

    try:
        namespaces = await asyncio.to_thread(_list_namespaces)
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []

    return _filter(ctx, [discord.OptionChoice(n.metadata.name) for n in namespaces.items])
