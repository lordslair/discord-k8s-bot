# -*- coding: utf8 -*-

import discord

from kubernetes import config, client
from loguru import logger


def k8s_list_namespaced_pod(ctx: discord.AutocompleteContext):
    try:
        config.load_kube_config("/etc/kubeconfig.yaml")
        pods = client.CoreV1Api().list_namespaced_pod(ctx.options["namespace"])
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []
    else:
        db_list = []
        for pod in pods.items:
            db_list.append(discord.OptionChoice(pod.metadata.name))
        return db_list


def k8s_list_namespace(ctx: discord.AutocompleteContext):
    try:
        config.load_kube_config("/etc/kubeconfig.yaml")
        namespaces = client.CoreV1Api().list_namespace()
    except Exception as e:
        logger.error(f'K8s Query KO [{e}]')
        return []
    else:
        db_list = []
        for namespace in namespaces.items:
            db_list.append(discord.OptionChoice(namespace.metadata.name))
        return db_list
