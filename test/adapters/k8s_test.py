import io
import json
import sys
import unittest
from unittest.mock import (
    patch,
)
from uuid import (
    uuid4,
)

sys.path.append('src')
from adapters import k8s
from adapters.k8s import (
    APIServer,
    PodStatus,
)


class GetPodStatusTest(unittest.TestCase):

    @patch('adapters.k8s.APIServer', autospec=True, spec_set=True)
    def test__returns_a_PodStatus_obj_if_resource_found(
            self,
            mock_api_server_cls):
        # Setup
        juju_unit = uuid4()

        mock_api_server = mock_api_server_cls.return_value
        mock_api_server.get.return_value = {
            'kind': 'PodList',
            'items': [{
                'metadata': {
                    'annotations': {
                        'juju.io/unit': juju_unit
                    }
                }
            }]
        }

        # Exercise
        pod_status = k8s.get_pod_status(juju_model=uuid4(),
                                        juju_app=uuid4(),
                                        juju_unit=juju_unit)

        # Assert
        assert type(pod_status) == PodStatus

    @patch('adapters.k8s.APIServer', autospec=True, spec_set=True)
    def test__returns_PodStatus_even_if_resource_not_found(
            self,
            mock_api_server_cls):
        # Setup
        mock_api_server = mock_api_server_cls.return_value
        mock_api_server.get.return_value = {
            'kind': 'PodList',
            'items': []
        }

        # Exercise
        pod_status = k8s.get_pod_status(juju_model=uuid4(),
                                        juju_app=uuid4(),
                                        juju_unit=uuid4())

        # Assert
        assert type(pod_status) == PodStatus


class APIServerTest(unittest.TestCase):

    @patch('adapters.k8s.open', create=True)
    @patch('adapters.k8s.ssl.SSLContext', autospec=True, spec_set=True)
    @patch('adapters.k8s.http.client.HTTPSConnection',
           autospec=True, spec_set=True)
    def test__get__loads_json_string_successfully(
            self,
            mock_https_connection_cls,
            mock_ssl_context_cls,
            mock_open):
        # Setup
        mock_token = f'{uuid4()}'
        mock_token_file = io.StringIO(mock_token)
        mock_open.return_value = mock_token_file
        mock_response_dict = {}
        mock_response_json = io.StringIO(json.dumps(mock_response_dict))

        mock_conn = mock_https_connection_cls.return_value
        mock_conn.getresponse.return_value = mock_response_json

        # Exercise
        api_server = APIServer()
        response = api_server.get('/some/path')

        # Assert
        assert response == mock_response_dict


class PodStatusTest(unittest.TestCase):

    def test__pod_is_not_running_yet(self):
        # Setup
        status_dict = {
            'metadata': {
                'annotations': {
                    'juju.io/unit': uuid4()
                }
            },
            'status': {
                'phase': 'Pending',
                'conditions': [{
                    'type': 'ContainersReady',
                    'status': 'False'
                }]
            }
        }

        # Exercise
        pod_status = PodStatus(status_dict=status_dict)

        # Assert
        assert not pod_status.is_unknown
        assert not pod_status.is_running
        assert not pod_status.is_ready

    def test__pod_is_ready(self):
        # Setup
        status_dict = {
            'metadata': {
                'annotations': {
                    'juju.io/unit': uuid4()
                }
            },
            'status': {
                'phase': 'Running',
                'conditions': [{
                    'type': 'ContainersReady',
                    'status': 'True'
                }]
            }
        }

        # Exercise
        pod_status = PodStatus(status_dict=status_dict)

        # Assert
        assert not pod_status.is_unknown
        assert pod_status.is_running
        assert pod_status.is_ready

    def test__pod_is_running_but_not_yet_ready_to_serve(self):
        # Setup
        status_dict = {
            'metadata': {
                'annotations': {
                    'juju.io/unit': uuid4()
                }
            },
            'status': {
                'phase': 'Running',
                'conditions': [{
                    'type': 'ContainersReady',
                    'status': 'False'
                }]
            }
        }

        # Exercise
        pod_status = PodStatus(status_dict=status_dict)

        # Assert
        assert not pod_status.is_unknown
        assert pod_status.is_running
        assert not pod_status.is_ready

    def test__status_is_unknown(self):
        # Exercise
        pod_status = PodStatus(status_dict=None)

        # Assert
        assert pod_status.is_unknown
        assert not pod_status.is_running
        assert not pod_status.is_ready
