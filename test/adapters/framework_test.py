from pathlib import Path
import pytest
import shutil
import sys
import tempfile
import unittest
from uuid import uuid4
from unittest.mock import (
    call,
    create_autospec,
    patch,
)
sys.path.append('lib')
from ops.charm import (
    CharmMeta,
)
from ops.framework import (
    Framework,
)
from ops.model import (
    BlockedStatus,
    Resources,
)

sys.path.append('src')
from adapters.framework import (
    _fetch_image_meta,
    FrameworkAdapter,
    ResourceError,
)


class FetchImageMetaTest(unittest.TestCase):

    def test__successful(self):
        # Setup
        mock_image_name = f"{uuid4()}"
        mock_image_path = f"{uuid4()}"
        mock_username = f"{uuid4()}"
        mock_password = f"{uuid4()}"

        mock_path_obj = create_autospec(Path, spec_set=True)
        mock_path_obj.exists.return_value = True
        mock_path_obj.read_text.return_value = f"""
        registrypath: {mock_image_path}
        username: {mock_username}
        password: {mock_password}
        """

        mock_resources_repo = create_autospec(Resources, set_spec=True)
        mock_resources_repo.fetch.return_value = mock_path_obj

        # Exercise
        image_meta = _fetch_image_meta(
            image_name=mock_image_name,
            resources_repo=mock_resources_repo
        )

        # Assert
        assert image_meta.image_path == mock_image_path
        assert image_meta.username == mock_username
        assert image_meta.password == mock_password

    def test__resource_path_does_not_exist(self):
        # Setup
        mock_image_name = f"{uuid4()}"

        mock_path_obj = create_autospec(Path, spec_set=True)
        mock_path_obj.exists.return_value = False

        mock_resources_repo = create_autospec(Resources, set_spec=True)
        mock_resources_repo.fetch.return_value = mock_path_obj

        # Exercise
        with pytest.raises(ResourceError) as err:
            _fetch_image_meta(
                image_name=mock_image_name,
                resources_repo=mock_resources_repo
            )

            assert type(err.status) == BlockedStatus
            assert err.status.message == \
                f'{mock_image_name}: Resource not found at ' \
                f'{str(mock_path_obj)}'

    def test__path_is_unreadable(self):
        # Setup
        mock_image_name = f"{uuid4()}"

        mock_path_obj = create_autospec(Path, spec_set=True)
        mock_path_obj.exists.return_value = True
        mock_path_obj.read_text.return_value = None

        mock_resources_repo = create_autospec(Resources, set_spec=True)
        mock_resources_repo.fetch.return_value = mock_path_obj

        # Exercise
        with pytest.raises(ResourceError) as err:
            _fetch_image_meta(
                image_name=mock_image_name,
                resources_repo=mock_resources_repo
            )

            assert type(err.status) == BlockedStatus
            assert err.status.message == \
                f'{mock_image_name}: Resource unreadable at ' \
                f'{str(mock_path_obj)}'

    def test__invalid_yaml(self):
        # Setup
        mock_image_name = f"{uuid4()}"

        mock_path_obj = create_autospec(Path, spec_set=True)
        mock_path_obj.exists.return_value = True
        mock_path_obj.read_text.return_value = """
            [Invalid YAML Here]
            something: something: else
            """

        mock_resources_repo = create_autospec(Resources, set_spec=True)
        mock_resources_repo.fetch.return_value = mock_path_obj

        # Exercise
        with pytest.raises(ResourceError) as err:
            _fetch_image_meta(
                image_name=mock_image_name,
                resources_repo=mock_resources_repo
            )

            assert type(err.status) == BlockedStatus
            assert err.status.message == \
                f'{mock_image_name}: Invalid YAML at ' \
                f'{str(mock_path_obj)}'


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

    def test__am_i_leader__returns_true_if_unit_is_leader(self):
        # Setup
        mock_framework = create_autospec(self.create_framework(),
                                         spec_set=True)
        mock_framework.model.unit.is_leader.return_value = True

        # Exercise
        adapter = FrameworkAdapter(mock_framework)
        is_leader = adapter.am_i_leader()

        # Assert
        assert is_leader

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

    @patch('adapters.framework._fetch_image_meta', spec_set=True)
    def test__get_image_meta__returns_an_image_meta_object(
            self, mock_fetch_image_meta_func):
        # Setup
        framework = self.create_framework()
        mock_framework = create_autospec(framework, spec_set=True)
        mock_framework.model = create_autospec(framework.model, spec_set=True)

        image_name = uuid4()

        # Exercise
        adapter = FrameworkAdapter(mock_framework)
        image_meta = adapter.get_image_meta(image_name)

        # Assert
        assert mock_fetch_image_meta_func.call_count == 1
        assert mock_fetch_image_meta_func.call_args == \
            call(image_name, mock_framework.model.resources)

        assert image_meta == mock_fetch_image_meta_func.return_value
