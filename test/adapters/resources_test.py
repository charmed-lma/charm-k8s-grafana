from pathlib import Path
import pytest
import sys
import unittest
from uuid import uuid4
from unittest.mock import (
    create_autospec,
)
sys.path.append('lib')
from ops.model import (
    BlockedStatus,
)

sys.path.append('src')
from adapters.resources import (
    get_image_meta,
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

        # Exercise
        image_meta = get_image_meta(
            image_name=mock_image_name,
            image_meta_path=mock_path_obj
        )

        # Assert
        assert image_meta.image_path == mock_image_path
        assert image_meta.repo_username == mock_username
        assert image_meta.repo_password == mock_password

    def test__resource_path_does_not_exist(self):
        # Setup
        mock_image_name = f"{uuid4()}"

        mock_path_obj = create_autospec(Path, spec_set=True)
        mock_path_obj.exists.return_value = False

        # Exercise
        with pytest.raises(ResourceError) as err:
            get_image_meta(
                image_name=mock_image_name,
                image_meta_path=mock_path_obj
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

        # Exercise
        with pytest.raises(ResourceError) as err:
            get_image_meta(
                image_name=mock_image_name,
                image_meta_path=mock_path_obj
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

        # Exercise
        with pytest.raises(ResourceError) as err:
            get_image_meta(
                image_name=mock_image_name,
                image_meta_path=mock_path_obj
            )

            assert type(err.status) == BlockedStatus
            assert err.status.message == \
                f'{mock_image_name}: Invalid YAML at ' \
                f'{str(mock_path_obj)}'
