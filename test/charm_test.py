from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import (
    call,
    create_autospec,
    patch
)

sys.path.append('lib')
from ops.charm import (
    CharmMeta,
)
from ops.framework import (
    EventBase,
    Framework
)

sys.path.append('src')
from charm import (
    Charm
)


class CharmTest(unittest.TestCase):

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

    @patch('charm.http_interface', spec_set=True, autospec=True)
    @patch('charm.handlers.on_config_changed', spec_set=True, autospec=True)
    @patch('charm.FrameworkAdapter', spec_set=True, autospec=True)
    def test__on_config_changed_delegator__it_blocks_until_pod_is_ready(
            self,
            mock_framework_adapter_cls,
            mock_on_config_changed_handler,
            mock_http_interface):
        # Setup
        mock_outputs = [
            SimpleNamespace(**dict(unit_status=object(), pod_is_ready=False)),
            SimpleNamespace(**dict(unit_status=object(), pod_is_ready=False)),
            SimpleNamespace(**dict(unit_status=object(), pod_is_ready=True)),
        ]
        mock_on_config_changed_handler.side_effect = mock_outputs
        mock_event = create_autospec(EventBase, spec_set=True)
        mock_adapter = mock_framework_adapter_cls.return_value

        # Exercise
        charm_obj = Charm(self.create_framework(), None)
        charm_obj.on_config_changed_delegator(mock_event)

        # Assert
        assert mock_on_config_changed_handler.call_count == len(mock_outputs)
        assert mock_on_config_changed_handler.call_args_list == [
            call(event=mock_event, app_name=mock_adapter.get_app_name()),
            call(event=mock_event, app_name=mock_adapter.get_app_name()),
            call(event=mock_event, app_name=mock_adapter.get_app_name()),
        ]
        assert mock_adapter.set_unit_status.call_count == len(mock_outputs)
        assert mock_adapter.set_unit_status.call_args_list == [
            call(mock_output.unit_status) for mock_output in mock_outputs
        ]

    # spec_set=True ensures we don't define an attribute that is not in the
    # real object, autospec=True automatically copies the signature of the
    # mocked object to the mock.
    @patch('charm.http_interface', spec_set=True, autospec=True)
    @patch('charm.handlers.on_start', spec_set=True, autospec=True)
    @patch('charm.GrafanaImageResource', spec_set=True, autospec=True)
    @patch('charm.FrameworkAdapter', spec_set=True, autospec=True)
    def test__on_start_delegator__spec_is_set(
            self,
            mock_framework_adapter_cls,
            mock_prometheus_image_resource_cls,
            mock_on_start_handler,
            mock_http_interface):

        # Setup
        mock_event = create_autospec(EventBase, spec_set=True)
        mock_adapter = mock_framework_adapter_cls.return_value
        mock_image_resource = mock_prometheus_image_resource_cls.return_value
        mock_output = create_autospec(object)
        mock_output.spec = create_autospec(object)
        mock_output.unit_status = create_autospec(object)
        mock_on_start_handler.return_value = mock_output

        # Exercise
        charm_obj = Charm(self.create_framework(), None)
        charm_obj.on_start_delegator(mock_event)

        # Assertions
        assert mock_adapter.get_config.call_count == 1
        assert mock_adapter.get_config.call_args == call()

        assert mock_on_start_handler.call_count == 1
        assert mock_on_start_handler.call_args == call(
            event=mock_event,
            app_name=mock_adapter.get_app_name.return_value,
            config=mock_adapter.get_config.return_value,
            image_resource=mock_image_resource)

        assert mock_adapter.set_pod_spec.call_count == 1
        assert mock_adapter.set_pod_spec.call_args == \
            call(mock_output.spec)

        assert mock_adapter.set_unit_status.call_count == 1
        assert mock_adapter.set_unit_status.call_args == \
            call(mock_output.unit_status)

    @patch('charm.http_interface', spec_set=True, autospec=True)
    @patch('charm.handlers.on_start', spec_set=True, autospec=True)
    @patch('charm.GrafanaImageResource', spec_set=True, autospec=True)
    @patch('charm.FrameworkAdapter', spec_set=True, autospec=True)
    def test__on_upgrade_delegator__it_updates_the_spec(
            self,
            mock_framework_adapter_cls,
            mock_prometheus_image_resource_cls,
            mock_on_start_handler,
            mock_http_interface):

        # Setup
        mock_event = create_autospec(EventBase, spec_set=True)
        mock_adapter = mock_framework_adapter_cls.return_value
        mock_image_resource = mock_prometheus_image_resource_cls.return_value
        mock_output = create_autospec(object)
        mock_output.spec = create_autospec(object)
        mock_output.unit_status = create_autospec(object)
        mock_on_start_handler.return_value = mock_output

        # Exercise
        charm_obj = Charm(self.create_framework(), None)
        charm_obj.on_upgrade_delegator(mock_event)

        # Assertions
        assert mock_adapter.get_config.call_count == 1
        assert mock_adapter.get_config.call_args == call()

        assert mock_on_start_handler.call_count == 1
        assert mock_on_start_handler.call_args == call(
            event=mock_event,
            app_name=mock_adapter.get_app_name.return_value,
            config=mock_adapter.get_config.return_value,
            image_resource=mock_image_resource)

        assert mock_adapter.set_pod_spec.call_count == 1
        assert mock_adapter.set_pod_spec.call_args == \
            call(mock_output.spec)

        assert mock_adapter.set_unit_status.call_count == 1
        assert mock_adapter.set_unit_status.call_args == \
            call(mock_output.unit_status)
