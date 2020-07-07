import random
import sys
import unittest
from unittest.mock import (
    call,
    create_autospec,
    patch,
)
from uuid import uuid4

sys.path.append('lib')

from ops.charm import (
    ConfigChangedEvent,
)
from ops.framework import (
    BoundStoredState,
    EventBase,
    StoredState,
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
    ServerDetails as PostgresServerDetails,
)
from interface_mysql import (
    MySQLServerDetails,
    NewMySQLRelationEvent,
)


class CharmTest(unittest.TestCase):

    def setUp(self):
        # Setup
        self.harness = Harness(charm.Charm)
        self.harness.begin()

    def test__init__works_without_a_hitch(self):
        # Setup
        harness = Harness(charm.Charm)

        # Exercise
        harness.begin()

    @patch('charm._on_server_new_relation_handler', spec_set=True, autospec=True)
    def test__mysql_on_new_relation__it_calls_the_handler_with_mysql_server_details(
            self,
            mocked_on_server_new_relation_handler):
        # Setup
        server_details = MySQLServerDetails(dict(
            host=str(uuid4()),
            port=random.randint(1, 65535),
            database=str(uuid4()),
            user=str(uuid4()),
            password=str(uuid4()),
        ))

        # Exercise
        self.harness.charm.mysql.on.new_relation.emit(server_details)

        # Assert
        assert mocked_on_server_new_relation_handler.call_count == 1

        args, kwargs = mocked_on_server_new_relation_handler.call_args
        assert kwargs['mysql_server_details'] == server_details.snapshot()

    def test__on_config_changed_calls_handler(self):
        with patch.object(charm, 'on_config_changed_handler',
                          spect_set=True) as mocked_on_config_changed_handler:
            # Exercise
            self.harness.update_config()

            # Assert
            assert mocked_on_config_changed_handler.call_count == 1

            args, kwargs = mocked_on_config_changed_handler.call_args
            assert isinstance(args[0], ConfigChangedEvent)
            assert isinstance(args[1], adapters.framework.FrameworkAdapter)

    def test__prometheus_client_on_new_server_available_calls_handler(self):
        with patch.object(charm, 'on_server_new_relation_handler',
                          spect_set=True) as mocked_on_new_server_relation_handler:
            # Setup
            server_details = PostgresServerDetails(
                host=str(uuid4()),
                port=random.randint(1, 65535),
            )

            # Exercise
            self.harness.charm.prometheus_client.on.server_available.emit(
                server_details)

            # Assert
            assert mocked_on_new_server_relation_handler.call_count == 1

            args, kwargs = mocked_on_new_server_relation_handler.call_args
            assert isinstance(args[0], ServerAvailableEvent)
            assert hasattr(args[0], 'server_details')
            assert args[0].server_details.host == server_details.host
            assert args[0].server_details.port == server_details.port
            assert isinstance(args[1], BoundStoredState)
            assert isinstance(args[2], adapters.framework.FrameworkAdapter)


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


class OnServerNewRelationHandlerTest(unittest.TestCase):

    @patch('charm.build_juju_pod_spec', spec_set=True, autospec=True)
    @patch('charm.interface_mysql.MySQLServerDetails',
           spec_set=True, autospec=True)
    @patch('charm.interface_http.ServerDetails',
           spec_set=True, autospec=True)
    def test__it_updates_the_juju_pod_spec(self,
                                           mock_prometheus_server_details_cls,
                                           mock_mysql_server_details_cls,
                                           mock_build_juju_pod_spec_func):
        # Setup
        mock_fw_adapter_cls = \
            create_autospec(adapters.framework.FrameworkAdapter,
                            spec_set=True)
        mock_fw = mock_fw_adapter_cls.return_value
        mock_fw.am_i_leader.return_value = True

        mock_event_cls = create_autospec(ServerAvailableEvent, spec_set=True)
        mock_event = mock_event_cls.return_value

        mock_state = create_autospec(StoredState).return_value
        mock_state.prometheus_server_details = {
            str(uuid4()): str(uuid4())
        }
        mock_prometheus_server_details = \
            mock_prometheus_server_details_cls.restore.return_value
        mock_state.mysql_server_details = {
            str(uuid4()): str(uuid4())
        }
        mock_mysql_server_details = \
            mock_mysql_server_details_cls.restore.return_value

        # Exercise
        charm.on_server_new_relation_handler(mock_event, mock_state, mock_fw)

        # Assert
        assert mock_build_juju_pod_spec_func.call_count == 1
        assert mock_build_juju_pod_spec_func.call_args == \
            call(app_name=mock_fw.get_app_name.return_value,
                 charm_config=mock_fw.get_config.return_value,
                 image_meta=mock_fw.get_image_meta.return_value,
                 prometheus_server_details=mock_prometheus_server_details,
                 mysql_server_details=mock_mysql_server_details)

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
