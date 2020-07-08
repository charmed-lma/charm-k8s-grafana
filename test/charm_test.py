import random
import sys
import unittest
from unittest.mock import (
    call,
    create_autospec,
    Mock,
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
    Unit,
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
    @patch('charm.fetch_image_meta', spec_set=True, autospec=True)
    def test__mysql_on_new_relation__it_calls_the_handler_with_mysql_server_details(
            self,
            mock_fetch_image_meta_func,
            mock_on_server_new_relation_handler):
        # Setup
        server_details = MySQLServerDetails(dict(
            host=str(uuid4()),
            port=random.randint(1, 65535),
            database=str(uuid4()),
            user=str(uuid4()),
            password=str(uuid4()),
        ))
        harness = self.harness
        harness.set_leader()
        harness.add_oci_resource('grafana-image')

        # Exercise
        harness.charm.mysql.on.new_relation.emit(server_details)

        # Assert
        assert mock_on_server_new_relation_handler.call_count == 1

        mysql_server_details_dict = server_details.snapshot()
        prometheus_server_details_dict = \
            dict(harness.charm.state.prometheus_server_details)
        assert mock_on_server_new_relation_handler.call_args == call(
            app_name=harness.charm.model.app.name,
            unit_is_leader=harness.charm.model.unit.is_leader(),
            mysql_server_details=mysql_server_details_dict,
            prometheus_server_details=prometheus_server_details_dict,
            image_meta=mock_fetch_image_meta_func.return_value,
            pod_obj=harness.framework.model.pod,
            unit_obj=harness.framework.model.unit
        )

    @patch('charm._on_config_changed_handler', spec_set=True, autospec=True)
    def test__on_config_changed__calls_on_config_changed_handler(
            self,
            mocked_on_config_changed_handler):
        # Exercise
        self.harness.update_config()

        # Assert
        assert mocked_on_config_changed_handler.call_count == 1
        assert mocked_on_config_changed_handler.call_args == call(
            model_name=self.harness.charm.model.name,
            app_name=self.harness.charm.model.app.name,
            unit_obj=self.harness.charm.model.unit,
        )

    @patch('charm._on_server_new_relation_handler', spec_set=True, autospec=True)
    @patch('charm.fetch_image_meta', spec_set=True, autospec=True)
    def test__prometheus_client_on_new_server_available_calls_handler(
            self,
            mock_fetch_image_meta_func,
            mock_on_server_new_relation_handler):
        # Setup
        harness = self.harness
        harness.add_oci_resource('grafana-image')
        server_details = PostgresServerDetails(
            host=str(uuid4()),
            port=random.randint(1, 65535),
        )

        # Exercise
        self.harness.charm.prometheus_client.on.server_available.emit(server_details)

        # Assert
        assert mock_on_server_new_relation_handler.call_count == 1

        mysql_server_details_dict = \
            dict(harness.charm.state.mysql_server_details)
        prometheus_server_details_dict = server_details.snapshot()
        assert mock_on_server_new_relation_handler.call_args == call(
            app_name=harness.charm.model.app.name,
            unit_is_leader=harness.charm.model.unit.is_leader(),
            mysql_server_details=mysql_server_details_dict,
            prometheus_server_details=prometheus_server_details_dict,
            image_meta=mock_fetch_image_meta_func.return_value,
            pod_obj=harness.framework.model.pod,
            unit_obj=harness.framework.model.unit
        )


class OnConfigChangedHandlerTest(unittest.TestCase):

    @patch('charm._update_unit_status_based_on_k8s_pod_status',
           spec_set=True, autospec=True)
    def test__it_calls_update_unit_status_correctly(
            self,
            mock_update_unit_status_func):
        # Setup
        model_name = str(uuid4())
        app_name = str(uuid4())
        unit_name = str(uuid4())
        unit_obj = create_autospec(Unit, isinstance=True)

        # Execute
        charm._on_config_changed_handler(
            model_name=model_name,
            app_name=app_name,
            unit_name=unit_name,
            unit_obj=unit_obj
        )

        # Assert
        mock_update_unit_status_func.call_count == 1
        mock_update_unit_status_func.call_args == call(
            juju_model_name=model_name,
            juju_app_name=app_name,
            juju_unit_name=unit_name,
            unit_obj=unit_obj)


class OnServerNewRelationHandlerTest(unittest.TestCase):

    @patch('charm.build_juju_pod_spec', spec_set=True, autospec=True)
    @patch('charm.interface_mysql.MySQLServerDetails', spec_set=True, autospec=True)
    @patch('charm.interface_http.ServerDetails', spec_set=True, autospec=True)
    @patch('charm._get_unit_status_setter', spec_set=True, autospec=True)
    def test__it_updates_the_juju_pod_spec(self,
                                           mock_get_unit_status_setter_func,
                                           mock_prometheus_server_details_cls,
                                           mock_mysql_server_details_cls,
                                           mock_build_juju_pod_spec_func):
        # Setup
        app_name = str(uuid4())
        mysql_server_details = {
            str(uuid4()): str(uuid4())
        }
        prometheus_server_details = {
            str(uuid4()): str(uuid4())
        }
        set_pod_spec_func = Mock()
        mock_image_meta = \
            create_autospec(adapters.framework.ImageMeta, spec_set=True).return_value

        # Exercise
        charm._on_server_new_relation_handler(
            app_name=app_name,
            unit_is_leader=True,
            mysql_server_details=mysql_server_details,
            prometheus_server_details=prometheus_server_details,
            image_meta=mock_image_meta,
            set_pod_spec_func=set_pod_spec_func,
            set_unit_status_func=mock_get_unit_status_setter_func.return_value
        )

        # Assert
        assert set_pod_spec_func.call_count == 1
        # assert mock_fw.set_pod_spec.call_args == \
        #     call(mock_build_juju_pod_spec_func.return_value)
        #
        # assert mock_fw.set_unit_status.call_count == 1
        # args, kwargs = mock_fw.set_unit_status.call_args_list[0]
        # assert type(args[0]) == MaintenanceStatus


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


class UpdateUnitStatusBasedOnK8sPodStatusTest(unittest.TestCase):
    @patch('charm.k8s', spec_set=True, autospec=True)
    @patch('charm.build_juju_unit_status', spec_set=True, autospec=True)
    def test__it_blocks_until_pod_is_ready(self,
                                           mock_build_juju_unit_status_func,
                                           mock_k8s_mod):
        # Setup
        mock_juju_unit_states = [
            MaintenanceStatus(str(uuid4())),
            MaintenanceStatus(str(uuid4())),
            ActiveStatus(str(uuid4())),
        ]
        mock_build_juju_unit_status_func.side_effect = mock_juju_unit_states

        mock_event_cls = create_autospec(EventBase, spec_set=True)
        mock_event = mock_event_cls.return_value

        # Exercise
        charm._on_config_changed_handler(mock_event, mock_fw)

        # Assert
        assert mock_fw.set_unit_status.call_count == len(mock_juju_unit_states)
        assert mock_fw.set_unit_status.call_args_list == [
            call(status) for status in mock_juju_unit_states
        ]
