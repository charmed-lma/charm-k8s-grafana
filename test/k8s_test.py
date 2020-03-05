import io
import json
import random
import sys
import unittest
from unittest.mock import (
    call,
    patch,
)
from uuid import (
    uuid4,
)

sys.path.append('src')
from k8s import (
    APIServer,
    PodStatus,
    ServiceSpec,
)


class APIServerTest(unittest.TestCase):

    @patch('k8s.open', create=True)
    @patch('k8s.ssl.SSLContext', autospec=True, spec_set=True)
    @patch('k8s.http.client.HTTPSConnection', autospec=True, spec_set=True)
    def test_get_loads_json_string_successfully(
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


class ServiceSpecTest(unittest.TestCase):

    @patch('k8s.os', autospec=True, spec_set=True)
    @patch('k8s.APIServer', autospec=True, spec_set=True)
    def test_fetch_is_succesfull(
            self,
            mock_api_server_cls,
            mock_os):
        # Setup
        app_name = f'{uuid4()}'
        mock_model_name = f'{uuid4()}'
        mock_os.environ = {
            'JUJU_MODEL_NAME': mock_model_name,
        }
        mock_port = random.randint(1, 65535)
        mock_cluster_ip = f'{uuid4()}'
        mock_api_server = mock_api_server_cls.return_value
        mock_api_server.get.return_value = {
            "kind": "Service",
            "apiVersion": "v1",
            "metadata": {
                "name": "charm-k8s-prometheus",
                "namespace": "lma",
                "uid": "5e5684e0-5870-450e-ab9d-ff840e0b10fb",
                "resourceVersion": "257015",
                "creationTimestamp": "2020-02-21T06:40:34Z",
                "labels": {
                    "juju-app": "charm-k8s-prometheus"
                },
                "annotations": {
                    "juju.io/model": "d3fb103b-515e-42c8-87f8-5ff26dd7a1e9"
                }
            },
            "spec": {
                "ports": [
                    {
                        "protocol": "TCP",
                        "port": mock_port,
                        "targetPort": 9090
                    }
                ],
                "selector": {
                    "juju-app": "charm-k8s-prometheus"
                },
                "clusterIP": f'{mock_cluster_ip}',
                "type": "ClusterIP",
                "sessionAffinity": "None"
            },
            "status": {
                "loadBalancer": {
                }
            }
        }

        # Exercise
        service_spec = ServiceSpec(app_name)
        service_spec.fetch()

        # Assert
        assert mock_api_server.get.call_count == 1
        assert mock_api_server.get.call_args == call(
            f'/api/v1/namespaces/{mock_model_name}/services/{app_name}'
        )

        assert service_spec.host == mock_cluster_ip
        assert service_spec.port == mock_port


class PodStatusTest(unittest.TestCase):

    @patch('k8s.os', autospec=True, spec_set=True)
    @patch('k8s.APIServer', autospec=True, spec_set=True)
    def test_pod_status_fetch_is_succesfull(
            self,
            mock_api_server_cls,
            mock_os):
        # Setup
        app_name = f'{uuid4()}'
        mock_model_name = f'{uuid4()}'
        mock_unit_name = f'{uuid4()}'
        mock_os.environ = {
            'JUJU_MODEL_NAME': mock_model_name,
            'JUJU_UNIT_NAME': mock_unit_name,
        }
        mock_api_server = mock_api_server_cls.return_value
        mock_api_server.get.return_value = {
            'kind': 'PodList',
            'items': [{
                'metadata': {
                    'annotations': {
                        'juju.io/unit': mock_unit_name
                    }
                },
                'status': {
                    'phase': 'Running',
                    'conditions': [{
                        'type': 'ContainersReady',
                        'status': 'True'
                    }]
                }
            }],
        }

        # Exercise
        pod_status = PodStatus(app_name)
        pod_status.fetch()

        # Assert
        assert mock_api_server.get.call_count == 1
        assert mock_api_server.get.call_args == call(
            f'/api/v1/namespaces/{mock_model_name}/pods?'
            f'labelSelector=juju-app={app_name}'
        )

        assert not pod_status.is_unknown
        assert pod_status.is_running
        assert pod_status.is_ready

    @patch('k8s.os', autospec=True, spec_set=True)
    @patch('k8s.APIServer', autospec=True, spec_set=True)
    def test_pod_status_api_server_did_not_return_a_pod_list_dict(
            self,
            mock_api_server_cls,
            mock_os):
        # Setup
        app_name = f'{uuid4()}'
        mock_model_name = f'{uuid4()}'
        mock_unit_name = f'{uuid4()}'
        mock_os.environ = {
            'JUJU_MODEL_NAME': mock_model_name,
            'JUJU_UNIT_NAME': mock_unit_name,
        }
        mock_api_server = mock_api_server_cls.return_value
        mock_api_server.get.return_value = {
            'kind': 'SomethingElse',
        }

        # Exercise
        pod_status = PodStatus(app_name)
        pod_status.fetch()

        assert pod_status.is_unknown
        assert not pod_status.is_running
        assert not pod_status.is_ready

    @patch('k8s.os', autospec=True, spec_set=True)
    @patch('k8s.APIServer', autospec=True, spec_set=True)
    def test_pod_status_pod_list_does_not_contain_pod_info(
            self,
            mock_api_server_cls,
            mock_os):
        # Setup
        app_name = f'{uuid4()}'
        mock_model_name = f'{uuid4()}'
        mock_unit_name = f'{uuid4()}'
        mock_os.environ = {
            'JUJU_MODEL_NAME': mock_model_name,
            'JUJU_UNIT_NAME': mock_unit_name,
        }
        mock_api_server = mock_api_server_cls.return_value
        mock_api_server.get.return_value = {
            'kind': 'PodList',
            'items': [{
                'metadata': {
                    'annotations': {
                        # Some other unit name
                        'juju.io/unit': f'{uuid4()}'
                    }
                },
                'status': {
                    'phase': 'Running',
                    'conditions': [{
                        'type': 'ContainersReady',
                        'status': 'True'
                    }]
                }
            }],
        }

        # Exercise
        pod_status = PodStatus(app_name)
        pod_status.fetch()

        # Assert
        assert pod_status.is_unknown
        assert not pod_status.is_running
        assert not pod_status.is_ready

    @patch('k8s.os', autospec=True, spec_set=True)
    @patch('k8s.APIServer', autospec=True, spec_set=True)
    def test_pod_status_pod_is_not_running_yet(
            self,
            mock_api_server_cls,
            mock_os):
        # Setup
        app_name = f'{uuid4()}'
        mock_model_name = f'{uuid4()}'
        mock_unit_name = f'{uuid4()}'
        mock_os.environ = {
            'JUJU_MODEL_NAME': mock_model_name,
            'JUJU_UNIT_NAME': mock_unit_name,
        }
        mock_api_server = mock_api_server_cls.return_value
        mock_api_server.get.return_value = {
            'kind': 'PodList',
            'items': [{
                'metadata': {
                    'annotations': {
                        'juju.io/unit': mock_unit_name
                    }
                },
                'status': {
                    'phase': 'Pending',
                    'conditions': [{
                        'type': 'ContainersReady',
                        'status': 'False'
                    }]
                }
            }],
        }

        # Exercise
        pod_status = PodStatus(app_name)
        pod_status.fetch()

        # Assert
        assert not pod_status.is_unknown
        assert not pod_status.is_running
        assert not pod_status.is_ready

    @patch('k8s.os', autospec=True, spec_set=True)
    @patch('k8s.APIServer', autospec=True, spec_set=True)
    def test_pod_status_pod_is_running_but_not_ready_to_serve_requests(
            self,
            mock_api_server_cls,
            mock_os):
        # Setup
        app_name = f'{uuid4()}'
        mock_model_name = f'{uuid4()}'
        mock_unit_name = f'{uuid4()}'
        mock_os.environ = {
            'JUJU_MODEL_NAME': mock_model_name,
            'JUJU_UNIT_NAME': mock_unit_name,
        }
        mock_api_server = mock_api_server_cls.return_value
        mock_api_server.get.return_value = {
            'kind': 'PodList',
            'items': [{
                'metadata': {
                    'annotations': {
                        'juju.io/unit': mock_unit_name
                    }
                },
                'status': {
                    'phase': 'Running',
                    'conditions': [{
                        'type': 'ContainersReady',
                        'status': 'False'
                    }]
                }
            }],
        }

        # Exercise
        pod_status = PodStatus(app_name)
        pod_status.fetch()

        # Assert
        assert not pod_status.is_unknown
        assert pod_status.is_running
        assert not pod_status.is_ready
