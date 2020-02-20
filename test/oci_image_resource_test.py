from pathlib import Path
import pytest
import sys
import unittest
from unittest.mock import (
    call,
    create_autospec,
)
from uuid import uuid4

sys.path.append('lib')
from ops.model import (
    BlockedStatus,
    Resources
)

sys.path.append('src')
from resources import (
    OCIImageResource,
    ResourceError,
)


class OCIImageResourceTest(unittest.TestCase):

    def test___fetch__succesfully_fetch_image_info(self):
        # Setup
        mock_resource_name = f"{uuid4()}"

        mock_image_path = f"{uuid4()}/{uuid4()}"
        mock_image_username = f"{uuid4()}"
        mock_image_password = f"{uuid4()}"

        mock_path_obj = create_autospec(Path, spec_set=True)
        mock_path_obj.exists.return_value = True
        mock_path_obj.read_text.return_value = f"""
        registrypath: {mock_image_path}
        username: {mock_image_username}
        password: {mock_image_password}
        """

        mock_resources_repo = create_autospec(Resources, set_spec=True)
        mock_resources_repo.fetch.return_value = mock_path_obj

        # Exercise
        image_resource = OCIImageResource(resource_name=mock_resource_name,
                                          resources_repo=mock_resources_repo)
        result = image_resource.fetch()

        # Assert
        assert mock_resources_repo.fetch.call_count == 1
        assert mock_resources_repo.fetch.call_args == \
            call(mock_resource_name)
        assert result
        assert image_resource.image_path == mock_image_path
        assert image_resource.username == mock_image_username
        assert image_resource.password == mock_image_password

    def test__fetch__resource_path_does_not_exist(self):
        # Setup
        mock_resource_name = f"{uuid4()}"

        mock_path_obj = create_autospec(Path, spec_set=True)
        mock_path_obj.exists.return_value = False

        mock_resources_repo = create_autospec(Resources, set_spec=True)
        mock_resources_repo.fetch.return_value = mock_path_obj

        # Exercise
        image_resource = OCIImageResource(resource_name=mock_resource_name,
                                          resources_repo=mock_resources_repo)
        with pytest.raises(ResourceError) as err:
            image_resource.fetch()

            assert type(err.status) == BlockedStatus
            assert err.status.message == \
                f'{mock_resource_name}: Resource not found at ' \
                f'{str(mock_path_obj)}'

        assert mock_resources_repo.fetch.call_count == 1
        assert mock_resources_repo.fetch.call_args == \
            call(mock_resource_name)

    def test__fetch__resource_path_is_unreadable(self):
        # Setup
        mock_resource_name = f"{uuid4()}"

        mock_path_obj = create_autospec(Path, spec_set=True)
        mock_path_obj.exists.return_value = True
        mock_path_obj.read_text.return_value = None

        mock_resources_repo = create_autospec(Resources, set_spec=True)
        mock_resources_repo.fetch.return_value = mock_path_obj

        # Exercise
        image_resource = OCIImageResource(resource_name=mock_resource_name,
                                          resources_repo=mock_resources_repo)
        with pytest.raises(ResourceError) as err:
            image_resource.fetch()

            assert type(err.status) == BlockedStatus
            assert err.status.message == \
                f'{mock_resource_name}: Resource unreadable at ' \
                f'{str(mock_path_obj)}'

        assert mock_path_obj.read_text.call_count == 1
        assert mock_path_obj.read_text.call_args == call()

    def test__fetch__invalid_yaml(self):
        # Setup
        mock_resource_name = f"{uuid4()}"

        mock_path_obj = create_autospec(Path, spec_set=True)
        mock_path_obj.exists.return_value = True
        mock_path_obj.read_text.return_value = """
            [Invalid YAML Here]
            something: something: else
            """

        mock_resources_repo = create_autospec(Resources, set_spec=True)
        mock_resources_repo.fetch.return_value = mock_path_obj

        # Exercise
        image_resource = OCIImageResource(resource_name=mock_resource_name,
                                          resources_repo=mock_resources_repo)
        with pytest.raises(ResourceError) as err:
            image_resource.fetch()

            assert type(err.status) == BlockedStatus
            assert err.status.message == \
                f'{mock_resource_name}: Invalid YAML at ' \
                f'{str(mock_path_obj)}'
