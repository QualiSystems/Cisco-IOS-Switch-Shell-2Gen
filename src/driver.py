#!/usr/bin/python
# -*- coding: utf-8 -*-
from cloudshell.shell.core.driver_context import (
    AutoLoadCommandContext,
    InitCommandContext,
    ResourceCommandContext,
)
from cloudshell.shell.core.driver_utils import GlobalLock
from cloudshell.shell.core.orchestration_save_restore import OrchestrationSaveRestore
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext
from cloudshell.shell.standards.networking.autoload_model import NetworkingResourceModel
from cloudshell.shell.standards.networking.driver_interface import (
    NetworkingResourceDriverInterface,
)
from cloudshell.shell.standards.networking.resource_config import (
    NetworkingResourceConfig,
)

from cloudshell.networking.cisco.cli.cisco_cli_handler import CiscoCli
from cloudshell.networking.cisco.flows.cisco_autoload_flow import (
    CiscoSnmpAutoloadFlow as AutoloadFlow,
)
from cloudshell.networking.cisco.flows.cisco_configuration_flow import (
    CiscoConfigurationFlow as ConfigurationFlow,
)
from cloudshell.networking.cisco.flows.cisco_connectivity_flow import (
    CiscoConnectivityFlow as ConnectivityFlow,
)
from cloudshell.networking.cisco.flows.cisco_load_firmware_flow import (
    CiscoLoadFirmwareFlow as FirmwareFlow,
)
from cloudshell.networking.cisco.flows.cisco_run_command_flow import (
    CiscoRunCommandFlow as CommandFlow,
)
from cloudshell.networking.cisco.flows.cisco_state_flow import (
    CiscoStateFlow as StateFlow,
)
from cloudshell.networking.cisco.snmp.cisco_snmp_handler import (
    CiscoSnmpHandler as SNMPHandler,
)


class CiscoIOSShellDriver(
    ResourceDriverInterface, NetworkingResourceDriverInterface, GlobalLock
):
    SUPPORTED_OS = [r"CAT[ -]?OS", r"IOS[ -]XE", r"IOS(?![ -]XR)"]
    SHELL_NAME = "Cisco IOS Switch 2G"

    def __init__(self):
        super(CiscoIOSShellDriver, self).__init__()
        self._cli = None

    def initialize(self, context: InitCommandContext):
        """Initialize method.

        :param context: an object with all Resource Attributes inside
        """
        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME, supported_os=self.SUPPORTED_OS, context=context
        )

        self._cli = CiscoCli(resource_config)
        return "Finished initializing"

    @GlobalLock.lock
    def get_inventory(self, context: AutoLoadCommandContext):
        """Return device structure with all standard attributes.

        :param context: an object with all Resource Attributes inside
        :return: response
        :rtype: str
        """
        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )
        cli_handler = self._cli.get_cli_handler(resource_config, logger)
        snmp_handler = SNMPHandler(resource_config, logger, cli_handler)

        autoload_operations = AutoloadFlow(logger=logger, snmp_handler=snmp_handler)
        logger.info("Autoload started")
        resource_model = NetworkingResourceModel(
            resource_config.name,
            resource_config.shell_name,
            resource_config.family_name,
        )

        response = autoload_operations.discover(
            resource_config.supported_os, resource_model
        )
        logger.info("Autoload completed")
        return response

    def run_custom_command(self, context: ResourceCommandContext, custom_command: str):
        """Send custom command.

        :param custom_command: Command user wants to send to the device.
        :param context: an object with all Resource Attributes inside
        :return: result
        :rtype: str
        """
        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )

        cli_handler = self._cli.get_cli_handler(resource_config, logger)
        send_command_operations = CommandFlow(
            logger=logger, cli_configurator=cli_handler
        )

        response = send_command_operations.run_custom_command(
            custom_command=custom_command
        )

        return response

    def run_custom_config_command(
        self, context: ResourceCommandContext, custom_command: str
    ):
        """Send custom command in configuration mode.

        :param custom_command: Command user wants to send to the device
        :param context: an object with all Resource Attributes inside
        :return: result
        :rtype: str
        """
        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )

        cli_handler = self._cli.get_cli_handler(resource_config, logger)
        send_command_operations = CommandFlow(
            logger=logger, cli_configurator=cli_handler
        )

        result_str = send_command_operations.run_custom_config_command(
            custom_command=custom_command
        )

        return result_str

    def ApplyConnectivityChanges(self, context: ResourceCommandContext, request: str):
        """
        Create vlan and add or remove it to/from network interface.

        :param context: an object with all Resource Attributes inside
        :param str request: request json
        :return:
        """
        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )

        cli_handler = self._cli.get_cli_handler(resource_config, logger)
        connectivity_operations = ConnectivityFlow(
            logger=logger,
            cli_handler=cli_handler,
            support_multi_vlan_str=True,
            support_vlan_range_str=True,
        )
        logger.info("Start applying connectivity changes.")
        result = connectivity_operations.apply_connectivity_changes(request=request)
        logger.info("Apply Connectivity changes completed")
        return result

    def save(
        self,
        context: ResourceCommandContext,
        folder_path: str,
        configuration_type: str,
        vrf_management_name: str,
    ):
        """Save selected file to the provided destination.

        :param context: an object with all Resource Attributes inside
        :param configuration_type: source file, which will be saved
        :param folder_path: destination path where file will be saved
        :param vrf_management_name: VRF management Name
        :return str saved configuration file name:
        """
        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )

        if not configuration_type:
            configuration_type = "running"

        if not vrf_management_name:
            vrf_management_name = resource_config.vrf_management_name

        cli_handler = self._cli.get_cli_handler(resource_config, logger)
        configuration_flow = ConfigurationFlow(
            cli_handler=cli_handler, logger=logger, resource_config=resource_config
        )
        logger.info("Save started")
        response = configuration_flow.save(
            folder_path=folder_path,
            configuration_type=configuration_type,
            vrf_management_name=vrf_management_name,
        )
        logger.info("Save completed")
        return response

    @GlobalLock.lock
    def restore(
        self,
        context: ResourceCommandContext,
        path: str,
        configuration_type: str,
        restore_method: str,
        vrf_management_name: str,
    ):
        """Restore selected file to the provided destination.

        :param context: an object with all Resource Attributes inside
        :param path: source config file
        :param configuration_type: running or startup configs
        :param restore_method: append or override methods
        :param vrf_management_name: VRF management Name
        """
        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )

        if not configuration_type:
            configuration_type = "running"

        if not restore_method:
            restore_method = "override"

        if not vrf_management_name:
            vrf_management_name = resource_config.vrf_management_name

        cli_handler = self._cli.get_cli_handler(resource_config, logger)
        configuration_flow = ConfigurationFlow(
            cli_handler=cli_handler, logger=logger, resource_config=resource_config
        )
        logger.info("Restore started")
        configuration_flow.restore(
            path=path,
            restore_method=restore_method,
            configuration_type=configuration_type,
            vrf_management_name=vrf_management_name,
        )
        logger.info("Restore completed")

    def orchestration_save(
        self, context: ResourceCommandContext, mode: str, custom_params: str
    ):
        """Save selected file to the provided destination.

        :param context: an object with all Resource Attributes inside
        :param mode: mode
        :param custom_params: json with custom save parameters
        :return str response: response json
        """
        if not mode:
            mode = "shallow"

        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )

        cli_handler = self._cli.get_cli_handler(resource_config, logger)
        configuration_flow = ConfigurationFlow(
            cli_handler=cli_handler, logger=logger, resource_config=resource_config
        )

        logger.info("Orchestration save started")
        response = configuration_flow.orchestration_save(
            mode=mode, custom_params=custom_params
        )
        response_json = OrchestrationSaveRestore(
            logger, resource_config.name
        ).prepare_orchestration_save_result(response)
        logger.info("Orchestration save completed")
        return response_json

    def orchestration_restore(
        self,
        context: ResourceCommandContext,
        saved_artifact_info: str,
        custom_params: str,
    ):
        """Restore selected file to the provided destination.

        :param context: an object with all Resource Attributes inside
        :param saved_artifact_info: OrchestrationSavedArtifactInfo json
        :param custom_params: json with custom restore parameters
        """
        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )

        cli_handler = self._cli.get_cli_handler(resource_config, logger)
        configuration_flow = ConfigurationFlow(
            cli_handler=cli_handler, logger=logger, resource_config=resource_config
        )

        logger.info("Orchestration restore started")
        restore_params = OrchestrationSaveRestore(
            logger, resource_config.name
        ).parse_orchestration_save_result(saved_artifact_info)
        configuration_flow.restore(**restore_params)
        logger.info("Orchestration restore completed")

    @GlobalLock.lock
    def load_firmware(
        self, context: ResourceCommandContext, path: str, vrf_management_name: str
    ):
        """Upload and updates firmware on the resource.

        :param context: an object with all Resource Attributes inside
        :param path: full path to firmware file, i.e. tftp://10.10.10.1/firmware.tar
        :param vrf_management_name: VRF management Name
        """
        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )

        if not vrf_management_name:
            vrf_management_name = resource_config.vrf_management_name

        cli_handler = self._cli.get_cli_handler(resource_config, logger)

        logger.info("Start Load Firmware")
        firmware_operations = FirmwareFlow(cli_handler=cli_handler, logger=logger)
        response = firmware_operations.load_firmware(
            path=path, vrf_management_name=vrf_management_name
        )
        logger.info("Finish Load Firmware: {}".format(response))

    def health_check(self, context: ResourceCommandContext):
        """Performs device health check.

        :param context: an object with all Resource Attributes inside
        :return: Success or Error message
        :rtype: str
        """
        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )
        cli_handler = self._cli.get_cli_handler(resource_config, logger)

        state_operations = StateFlow(
            logger=logger,
            api=api,
            resource_config=resource_config,
            cli_configurator=cli_handler,
        )
        return state_operations.health_check()

    def cleanup(self):
        pass

    def shutdown(self, context: ResourceCommandContext):
        """Shutdown device.

        :param context: an object with all Resource Attributes inside
        :return:
        """
        logger = LoggingSessionContext.get_logger_with_thread_id(context)
        api = CloudShellSessionContext(context).get_api()

        resource_config = NetworkingResourceConfig.from_context(
            shell_name=self.SHELL_NAME,
            supported_os=self.SUPPORTED_OS,
            context=context,
            api=api,
        )

        cli_handler = self._cli.get_cli_handler(resource_config, logger)
        state_operations = StateFlow(
            logger=logger,
            api=api,
            resource_config=resource_config,
            cli_configurator=cli_handler,
        )

        return state_operations.shutdown()
