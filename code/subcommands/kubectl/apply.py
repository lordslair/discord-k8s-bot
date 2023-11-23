# -*- coding: utf8 -*-

import discord

from discord.commands import option
from discord.ext import commands
from kubernetes import config
from loguru import logger

from subcommands.kubectl._autocomplete import (
    k8s_list_namespace,
)


def apply(group_kubectl, bot):
    @group_kubectl.command(
        description='Apply a configuration to a resource.',
        default_permission=False,
        name='apply',
        )
    @commands.guild_only()  # Hides the command from the menu in DMs
    @commands.has_any_role('Team')
    @option(
        "namespace",
        description="Namespace",
        autocomplete=k8s_list_namespace
        )
    async def apply(
        ctx,
        namespace: str,
    ):
        await ctx.defer(ephemeral=True)  # To defer answer (default: 15min)
        logger.info(
            f'[#{ctx.channel.name}][{ctx.author.name}] '
            f'/{group_kubectl} apply [{namespace}]'
            )

        try:
            config.load_kube_config("/etc/k8s/kubeconfig.yaml")
        except Exception as e:
            logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Load KO [{e}]')
        else:
            pass

        """
        from kubernetes import client, utils

        yaml_file = f'/tmp/kubernetes/{app}/{kind}-{app}.yaml'
        dep = yaml.safe_load(yaml_file)
        k8s_client = client.ApiClient()
        utils.create_from_yaml(k8s_client, yaml_file)
        resp = client.CoreV1Api().create_namespaced_deployment(
            body=dep,
            namespace=namespace,
            )
        print("Deployment created. status='%s'" % str(resp.status))
        k8s_api = client.ExtensionsV1beta1Api(k8s_client)
        deps = k8s_api.read_namespaced_deployment(
            f"sep-backend-{app}",
            namespace,
            )
        print("Deployment {0} created".format(deps.metadata.name))
        """

        await ctx.respond(
            embed=discord.Embed(
                title=f'kubectl apply [{namespace}]',
                description='Not implemented yet.',
                colour=discord.Colour.orange()
                ),
            )
        return
