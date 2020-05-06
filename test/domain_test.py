import random
import sys
import unittest
from uuid import uuid4
sys.path.append('src')
import domain
from adapters.framework import (
    ImageMeta,
)


class BuildJujuPodSpecTest(unittest.TestCase):

    def test_pod_spec_is_generated(self):
        # Set up
        mock_app_name = f'{uuid4()}'

        mock_advertised_port = random.randint(1, 65535)

        mock_config = {
            'advertised-port': mock_advertised_port,
        }

        mock_image_meta = ImageMeta({
            'registrypath': str(uuid4()),
            'username': str(uuid4()),
            'password': str(uuid4()),
        })

        # Exercise
        spec = domain.build_juju_pod_spec(app_name=mock_app_name,
                                          charm_config=mock_config,
                                          image_meta=mock_image_meta)

        # Assertions
        assert type(spec) == dict
        assert spec == {'containers': [{
            'name': mock_app_name,
            'imageDetails': {
                'imagePath': mock_image_meta.image_path,
                'username': mock_image_meta.repo_username,
                'password': mock_image_meta.repo_password
            },
            'ports': [{
                'containerPort': mock_advertised_port,
                'protocol': 'TCP'
            }],
            'readinessProbe': {
                'httpGet': {
                    'path': '/api/health',
                    'port': mock_advertised_port
                },
                'initialDelaySeconds': 10,
                'timeoutSeconds': 30
            }
        }]}
