import sys
import unittest
from unittest.mock import (
    call,
    create_autospec,
    patch,
)
from uuid import uuid4

sys.path.append('lib')

from ops.framework import (
    EventBase,
)
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)
from ops.testing import (
    Harness,
)

sys.path.append('src')
import adapters
import charm
from interface_http import (
    ServerAvailableEvent,
)


class CharmTest(unittest.TestCase):

    def test__init__works_without_a_hitch(self):
        # Setup
        harness = Harness(charm.Charm)

        # Exercise
        harness.begin()

        # Assert
        # None necessary for this test

    def test__on_start__it_sets_the_pod_spec_and_unit_status(self):
        # Setup
        harness = Harness(charm.Charm)
        harness.begin()

        # Exercise
        harness.charm.on.start.emit()

        # Assert
        # How to check if framework.model.pod.set_spec() and
        # framework.model.unit.status were called/set correctly?


class OnConfigChangedHandlerTest(unittest.TestCase):

    @patch('charm.k8s', spec_set=True, autospec=True)
    @patch('charm.build_juju_unit_status', spec_set=True, autospec=True)
    def test__it_blocks_until_pod_is_ready(self,
                                           mock_build_juju_unit_status_func,
                                           mock_k8s_mod):
        # Setup
        mock_fw_adapter_cls = \
            create_autospec(adapters.framework.FrameworkAdapter,
                            spec_set=True)
        mock_fw = mock_fw_adapter_cls.return_value

        mock_juju_unit_states = [
            MaintenanceStatus(str(uuid4())),
            MaintenanceStatus(str(uuid4())),
            ActiveStatus(str(uuid4())),
        ]
        mock_build_juju_unit_status_func.side_effect = mock_juju_unit_states

        mock_event_cls = create_autospec(EventBase, spec_set=True)
        mock_event = mock_event_cls.return_value

        # Exercise
        charm.on_config_changed_handler(mock_event, mock_fw)

        # Assert
        assert mock_fw.set_unit_status.call_count == len(mock_juju_unit_states)
        assert mock_fw.set_unit_status.call_args_list == [
            call(status) for status in mock_juju_unit_states
        ]


class OnPromAvailableHandlerTest(unittest.TestCase):

    @patch('charm.build_juju_pod_spec', spec_set=True, autospec=True)
    def test__it_updates_the_juju_pod_spec(self,
                                           mock_build_juju_pod_spec_func):
        # Setup
        mock_fw_adapter_cls = \
            create_autospec(adapters.framework.FrameworkAdapter,
                            spec_set=True)
        mock_fw = mock_fw_adapter_cls.return_value
        mock_fw.am_i_leader.return_value = True

        mock_event_cls = create_autospec(ServerAvailableEvent, spec_set=True)
        mock_event = mock_event_cls.return_value

        # Exercise
        charm.on_prom_available_handler(mock_event, mock_fw)

        # Assert
        assert mock_build_juju_pod_spec_func.call_count == 1
        assert mock_build_juju_pod_spec_func.call_args == \
            call(app_name=mock_fw.get_app_name.return_value,
                 charm_config=mock_fw.get_config.return_value,
                 image_meta=mock_fw.get_image_meta.return_value,
                 prometheus_server_details=mock_event.server_details)

        assert mock_fw.set_pod_spec.call_count == 1
        assert mock_fw.set_pod_spec.call_args == \
            call(mock_build_juju_pod_spec_func.return_value)

        assert mock_fw.set_unit_status.call_count == 1
        args, kwargs = mock_fw.set_unit_status.call_args_list[0]
        assert type(args[0]) == MaintenanceStatus


class OnStartHandlerTest(unittest.TestCase):

    @patch('charm.build_juju_pod_spec', spec_set=True, autospec=True)
    def test__it_updates_the_juju_pod_spec(self,
                                           mock_build_juju_pod_spec_func):
        # Setup
        mock_fw_adapter_cls = \
            create_autospec(adapters.framework.FrameworkAdapter,
                            spec_set=True)
        mock_fw = mock_fw_adapter_cls.return_value
        mock_fw.am_i_leader.return_value = True

        mock_event_cls = create_autospec(EventBase, spec_set=True)
        mock_event = mock_event_cls.return_value

        # Exercise
        charm.on_start_handler(mock_event, mock_fw)

        # Assert
        assert mock_build_juju_pod_spec_func.call_count == 1
        assert mock_build_juju_pod_spec_func.call_args == \
            call(app_name=mock_fw.get_app_name.return_value,
                 charm_config=mock_fw.get_config.return_value,
                 image_meta=mock_fw.get_image_meta.return_value)

        assert mock_fw.set_pod_spec.call_count == 1
        assert mock_fw.set_pod_spec.call_args == \
            call(mock_build_juju_pod_spec_func.return_value)

        assert mock_fw.set_unit_status.call_count == 1
        args, kwargs = mock_fw.set_unit_status.call_args_list[0]
        assert type(args[0]) == MaintenanceStatus
