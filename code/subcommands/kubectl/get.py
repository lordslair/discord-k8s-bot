# -*- coding: utf8 -*-

import discord

from discord.commands import option
from discord.ext import commands
from kubernetes import config, client
from loguru import logger

from subcommands.kubectl._autocomplete import k8s_list_namespace
from variables import DISCORD_ROLE


def get(group_kubectl, bot):
    @group_kubectl.command(
        description='Display one or many resources.',
        default_permission=False,
        name='get',
        )
    @commands.guild_only()  # Hides the command from the menu in DMs
    @commands.has_any_role(DISCORD_ROLE)
    @option(
        "namespace",
        description="Namespace",
        autocomplete=k8s_list_namespace
        )
    @option(
        "resource",
        description="Resource type",
        choices=[
            discord.OptionChoice('deployments'),
            discord.OptionChoice('pods'),
            discord.OptionChoice('pvc'),
            discord.OptionChoice('services'),
            ],
        )
    async def get(
        ctx,
        namespace: str,
        resource: str,
    ):
        await ctx.defer(ephemeral=True)  # To defer answer (default: 15min)
        logger.info(
            f'[#{ctx.channel.name}][{ctx.author.name}] '
            f'/{group_kubectl} get {namespace} {resource}'
            )

        try:
            config.load_kube_config("/etc/k8s/kubeconfig.yaml")
        except Exception as e:
            logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Load KO [{e}]')
        else:
            pass

        if resource == 'pods':
            try:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query')
                resources = client.CoreV1Api().list_namespaced_pod(namespace)
                logger.debug(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query Ended')
            except Exception as e:
                logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query KO [{e}]')
                embed = discord.Embed(
                    description='Command aborted: K8s Query KO',
                    colour=discord.Colour.red()
                    )
                await ctx.respond(embed=embed)
                return
            else:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query OK')

            # We got the resources object, we can start working
            description = ''
            embed = discord.Embed(
                title=f'kubectl get pods [{namespace}]',
                description=description,
                colour=discord.Colour.green()
                )

            # We Start to update the Embed
            await ctx.interaction.edit_original_response(embed=embed)
            # We loop over pods to have detailed infos
            for pod in resources.items:
                # We skip CronJob generated pods
                if 'job-name' in pod.metadata.labels:
                    continue

                description += f"`{pod.metadata.name}`\n"
                logger.trace(pod.metadata.name)

                for c in pod.status.container_statuses:
                    if c.ready:
                        status = '🟩 '
                    else:
                        status = '🟥 '
                    logger.trace(f"> {status} {c.name} ({c.restart_count})")
                    description += f"> {status} `{c.name} ({c.restart_count})`\n"

            # We update the Embed with the pod result
            embed = discord.Embed(
                title=f'kubectl get pods [{namespace}]',
                description=description,
                colour=discord.Colour.green()
                )
            await ctx.interaction.edit_original_response(embed=embed)
            return
        elif resource == 'pvc':
            try:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query')
                resources = client.CoreV1Api().list_namespaced_persistent_volume_claim(namespace)
                logger.debug(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query Ended')
            except Exception as e:
                logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query KO [{e}]')
                embed = discord.Embed(
                    description='Command aborted: K8s Query KO',
                    colour=discord.Colour.red()
                    )
                await ctx.respond(embed=embed)
                return
            else:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query OK')

            if len(resources.items) == 0:
                msg = 'No pvc were found for this namespace'
                logger.debug(msg)
                embed = discord.Embed(
                    description=msg,
                    colour=discord.Colour.orange()
                    )
                await ctx.respond(embed=embed)
                return

            # We got the resources object, we can start working
            description = ''
            embed = discord.Embed(
                title=f'kubectl get pvc [{namespace}]',
                description=description,
                colour=discord.Colour.green()
                )

            # We Start to update the Embed
            await ctx.interaction.edit_original_response(embed=embed)
            # We loop over pods to have detailed infos
            for pvc in resources.items:
                if pvc.status.phase == 'Bound':
                    status = '🟩 '
                else:
                    status = '⬜ '
                label = f"{pvc.metadata.name} ({pvc.status.capacity['storage']})"
                description += f"{status} `{label}`\n"
                logger.trace(f"{status} {label}")

            # We update the Embed with the pod result
            embed = discord.Embed(
                title=f'kubectl get pvc [{namespace}]',
                description=description,
                colour=discord.Colour.green()
                )
            await ctx.interaction.edit_original_response(embed=embed)
            return
        elif resource == 'deployments':
            try:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query')
                resources = client.AppsV1Api().list_namespaced_deployment(namespace)
                logger.debug(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query Ended')
            except Exception as e:
                logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query KO [{e}]')
                embed = discord.Embed(
                    description='Command aborted: K8s Query KO',
                    colour=discord.Colour.red()
                    )
                await ctx.respond(embed=embed)
                return
            else:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query OK')

            if len(resources.items) == 0:
                msg = 'No deployment were found for this namespace'
                logger.debug(msg)
                embed = discord.Embed(
                    description=msg,
                    colour=discord.Colour.orange()
                    )
                await ctx.respond(embed=embed)
                return

            # We got the resources object, we can start working
            description = ''
            embed = discord.Embed(
                title=f'kubectl get deployment [{namespace}]',
                description=description,
                colour=discord.Colour.green()
                )

            # We Start to update the Embed
            await ctx.interaction.edit_original_response(embed=embed)
            # We loop over pods to have detailed infos
            for deployment in resources.items:
                if deployment.spec.replicas == deployment.status.available_replicas:
                    status = '🟩 '
                else:
                    status = '🟥 '
                count = f"{deployment.status.available_replicas}/{deployment.spec.replicas}"
                description += f"{status} `{deployment.metadata.name} ({count})`\n"
                logger.trace(f"{status} {deployment.metadata.name} ({count})")

            # We update the Embed with the pod result
            embed = discord.Embed(
                title=f'kubectl get deployment [{namespace}]',
                description=description,
                colour=discord.Colour.green()
                )
            await ctx.interaction.edit_original_response(embed=embed)
            return
        elif resource == 'services':
            try:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query')
                resources = client.CoreV1Api().list_namespaced_service(namespace)
                logger.debug(f'[#{ctx.channel.name}][{ctx.author.name}] ├──> K8s Query Ended')
            except Exception as e:
                logger.error(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query KO [{e}]')
                embed = discord.Embed(
                    description='Command aborted: K8s Query KO',
                    colour=discord.Colour.red()
                    )
                await ctx.respond(embed=embed)
                return
            else:
                logger.info(f'[#{ctx.channel.name}][{ctx.author.name}] └──> K8s Query OK')

            if len(resources.items) == 0:
                msg = 'No services were found for this namespace'
                logger.debug(msg)
                embed = discord.Embed(
                    description=msg,
                    colour=discord.Colour.orange()
                    )
                await ctx.respond(embed=embed)
                return

            # We got the resources object, we can start working
            description = ''
            embed = discord.Embed(
                title=f'kubectl get services [{namespace}]',
                description=description,
                colour=discord.Colour.green()
                )

            # We Start to update the Embed
            await ctx.interaction.edit_original_response(embed=embed)
            # We loop over pods to have detailed infos
            for service in resources.items:
                description += f"`{service.metadata.name} ({service.spec.type})`\n"
                logger.trace(f"{service.metadata.name} ({service.spec.type})")

                for service_port in service.spec.ports:
                    src = f"{service.spec.cluster_ip}:{service_port.port}"
                    if hasattr(service_port, 'name'):
                        dst = f"{service_port.name}:{service_port.target_port}"
                    else:
                        dst = f"None:{service_port.target_port}"
                    logger.trace(f"> {src} -> {dst}")
                    description += f"> `{src} -> {dst}`\n"

                # Specific for Loadbalancers
                if service.spec.type == 'LoadBalancer':
                    for ingress in service.status.load_balancer.ingress:
                        logger.trace(f"> hostname: {ingress.hostname}")
                        description += f"> `hostname: {ingress.hostname}`\n"

            # We update the Embed with the pod result
            embed = discord.Embed(
                title=f'kubectl get services [{namespace}]',
                description=description,
                colour=discord.Colour.green()
                )
            await ctx.interaction.edit_original_response(embed=embed)
            return

        else:
            pass
