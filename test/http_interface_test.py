from pathlib import Path
import shutil
import random
import sys
import tempfile
import unittest
from unittest.mock import (
    call,
    Mock,
    patch,
)
from uuid import uuid4

sys.path.append('lib')
from ops.charm import (
    CharmMeta,
)
from ops.framework import (
    Framework
)

sys.path.append('src')
from http_interface import (
    Client,
    ServerAvailableEvent,
    ServerDetails,
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

    @patch('http_interface.FrameworkAdapter', autospec=True, spec_set=True)
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
