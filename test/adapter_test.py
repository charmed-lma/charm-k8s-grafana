from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from uuid import uuid4
from unittest.mock import (
    create_autospec,
)
sys.path.append('lib')
from ops.charm import (
    CharmMeta,
)
from ops.framework import (
    Framework,
)

sys.path.append('src')
from adapters import (
    FrameworkAdapter,
)


class FrameworkAdapterTest(unittest.TestCase):

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

    def test__get_app_name__returns_the_name_of_the_app(self):
        # Setup
        mock_framework = create_autospec(self.create_framework(),
                                         spec_set=True)
        mock_app_name = f'{uuid4()}'
        mock_framework.model.app.name = mock_app_name

        # Exercise
        adapter = FrameworkAdapter(mock_framework)
        app_name = adapter.get_app_name()

        # Assert
        assert app_name == mock_app_name

    def test__get_config__returns_a_value_given_a_key(self):
        # Setup
        mock_framework = create_autospec(self.create_framework(),
                                         spec_set=True)
        mock_key = f'{uuid4()}'
        mock_value = f'{uuid4()}'
        mock_framework.model.config = {
            mock_key: mock_value
        }

        # Exercise
        adapter = FrameworkAdapter(mock_framework)
        value = adapter.get_config(mock_key)

        # Assert
        assert value == mock_value

    def test__get_config__returns_the_config_dict_when_no_key_given(self):
        # Setup
        mock_framework = create_autospec(self.create_framework(),
                                         spec_set=True)
        mock_config = {
            f'{uuid4()}': f'{uuid4()}',
            f'{uuid4()}': f'{uuid4()}',
            f'{uuid4()}': f'{uuid4()}',
            f'{uuid4()}': f'{uuid4()}',
        }
        mock_framework.model.config = mock_config

        # Exercise
        adapter = FrameworkAdapter(mock_framework)
        config = adapter.get_config()

        # Assert
        assert config == mock_config
