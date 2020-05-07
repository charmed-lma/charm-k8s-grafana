from pathlib import Path
import shutil
import random
import sys
import tempfile
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
    CharmMeta,
)
from ops.framework import (
    EventBase,
    Framework
)

sys.path.append('src')
from interface_http import (
    Client,
    ClientEvents,
    ServerAvailableEvent,
    ServerDetails,
)
from adapters import (
    k8s
)


class ServerDetailsTest(unittest.TestCase):

    def test__init__initializes_host_and_port_by_default(self):
        # Exercise
        server_details = ServerDetails()

        # Assertions
        assert server_details.host is None
        assert server_details.port is None

    def test__init__sets_host_and_port_info(self):
        # Set up
        mock_port = random.randint(1, 65535)
        mock_host = f'{uuid4()}'

        # Exercise
        server_details = ServerDetails(host=mock_host,
                                       port=mock_port)

        # Assertions
        assert server_details.host == mock_host
        assert server_details.port == mock_port

    def test__set_address__sets_host_and_port_info(self):
        # Set up
        mock_port = random.randint(1, 65535)
        mock_host = f'{uuid4()}'

        # Exercise
        server_details = ServerDetails()
        server_details.set_address(host=mock_host,
                                   port=mock_port)

        # Assertions
        assert server_details.host == mock_host
        assert server_details.port == mock_port

    def test__snapshot__returns_a_dict_of_strings(self):
        # Set up
        mock_port = random.randint(1, 65535)
        mock_host = f'{uuid4()}'
        server_details = ServerDetails(host=mock_host,
                                       port=mock_port)

        # Exercise
        snapshot = server_details.snapshot()

        # Assertions
        assert snapshot == {
            'server_details.host': server_details.host,
            'server_details.port': server_details.port,
        }

    def test__restore__restores_from_snapshot(self):
        # Set up
        mock_port = random.randint(1, 65535)
        mock_host = f'{uuid4()}'
        snapshot = {
            'server_details.host': mock_host,
            'server_details.port': mock_port,
        }

        # Exercise
        server_details = ServerDetails.restore(snapshot)

        # Assertions
        assert server_details.host == mock_host
        assert server_details.port == mock_port


class ServerAvailableEventTest(unittest.TestCase):

    def test__init__sets_the_server_details(self):
        # Set up
        handle = Mock()
        server_details = ServerDetails()

        # Exercise
        event = ServerAvailableEvent(handle, server_details)

        # Assertions
        assert event.server_details == server_details

    def test__restore__restores_from_a_server_details_snapshot(self):
        # Set up
        handle = Mock()
        port = random.randint(1, 65535)
        host = f'{uuid4()}'
        server_details = ServerDetails(host=host, port=port)

        # Exercise
        event = ServerAvailableEvent(handle, ServerDetails())
        event.restore(server_details.snapshot())

        # Assertions
        assert event.server_details.snapshot() == server_details.snapshot()

    def test__snapshot__returns_a_snapshot_of_server_details(self):
        # Set up
        handle = Mock()
        port = random.randint(1, 65535)
        host = f'{uuid4()}'
        server_details = ServerDetails(host=host, port=port)

        # Exercise
        event = ServerAvailableEvent(handle, server_details)
        snapshot = event.snapshot()

        # Assertions
        assert snapshot == server_details.snapshot()


class ClientTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        # Ensure that we clean up the tmp directory even when the test
        # fails or errors out for whatever reason.
        self.addCleanup(shutil.rmtree, self.tmpdir)

    def create_framework(self):
        framework = Framework(self.tmpdir / "framework.data",
                              self.tmpdir, CharmMeta(), None)
        # Ensure that the Framework object is closed and cleaned up even
        # when the test fails or errors out.
        self.addCleanup(framework.close)

        return framework

    @patch('interface_http.framework.FrameworkAdapter',
           autospec=True, spec_set=True)
    def test__init__observes_the_relation_changed_event(
            self,
            mock_framework_adapter_cls):
        # Set up
        mock_adapter = mock_framework_adapter_cls.return_value
        mock_relation_name = f'{uuid4()}'
        mock_charm = Mock()
        mock_charm.on = {mock_relation_name: Mock()}

        # Exercise
        client = Client(mock_charm, mock_relation_name)

        # Assertions
        assert client.relation_name == mock_relation_name
        assert mock_adapter.observe.call_count == 1
        assert mock_adapter.observe.call_args == call(
            mock_charm.on[mock_relation_name].relation_changed,
            client.on_relation_changed
        )

    @patch('interface_http.framework.FrameworkAdapter',
           autospec=True, spec_set=True)
    @patch('interface_http.k8s', autospec=True, spec_set=True)
    def test__on_relation_change__emits_the_correct_server_details(
            self,
            mock_k8s_mod,
            mock_framework_adapter_cls):
        # Set up
        mock_relation_name = f'{uuid4()}'
        mock_charm = Mock()
        mock_charm.on = {mock_relation_name: Mock()}
        mock_event = create_autospec(EventBase, spec_set=True)

        mock_service_spec = create_autospec(k8s.ServiceSpec, spec_set=True)
        mock_k8s_mod.get_service_spec.return_value = mock_service_spec

        mock_emit_method = Mock()
        mock_server_available_attr = Mock()
        mock_server_available_attr.emit = mock_emit_method
        mock_client_events_cls = create_autospec(ClientEvents, spec_set=True)
        mock_client_events = mock_client_events_cls.return_value
        mock_client_events.server_available = mock_server_available_attr

        # Exercise
        client = Client(mock_charm, mock_relation_name)

        with patch.object(Client, 'on', mock_client_events):
            client.on_relation_changed(mock_event)

        # Assertions
        assert mock_emit_method.call_count == 1

        args, kwargs = mock_emit_method.call_args
        assert args[0].host == mock_service_spec.host
        assert args[0].port == mock_service_spec.port
