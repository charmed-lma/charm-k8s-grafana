import random
import sys
import textwrap
import unittest
from uuid import uuid4
sys.path.append('src')
import domain
from adapters.framework import (
    ImageMeta,
)
import interface_http
import interface_mysql


class BuildJujuPodSpecTest(unittest.TestCase):

    def setUp(self):
        self.mock_app_name = str(uuid4())
        self.mock_advertised_port = random.randint(1, 65535)
        self.mock_config = {
            'advertised-port': self.mock_advertised_port,
        }
        self.mock_image_meta = ImageMeta({
            'registrypath': str(uuid4()),
            'username': str(uuid4()),
            'password': str(uuid4()),
        })
        self.mock_prometheus_server_details = interface_http.ServerDetails(
            host=str(uuid4()),
            port=random.randint(1, 65535)
        )
        self.mock_mysql_server_details = interface_mysql.MySQLServerDetails(
            dict(
                host=str(uuid4()),
                port=random.randint(1, 65535),
                database=str(uuid4()),
                username=str(uuid4()),
                password=str(uuid4()),
            )
        )

    def test_pod_spec_is_generated(self):
        # Exercise
        spec = domain.build_juju_pod_spec(app_name=self.mock_app_name,
                                          charm_config=self.mock_config,
                                          image_meta=self.mock_image_meta)

        # Assertions
        assert type(spec) == dict
        assert spec == {'containers': [{
            'name': self.mock_app_name,
            'imageDetails': {
                'imagePath': self.mock_image_meta.image_path,
                'username': self.mock_image_meta.repo_username,
                'password': self.mock_image_meta.repo_password
            },
            'ports': [{
                'containerPort': self.mock_advertised_port,
                'protocol': 'TCP'
            }],
            'readinessProbe': {
                'httpGet': {
                    'path': '/api/health',
                    'port': self.mock_advertised_port
                },
                'initialDelaySeconds': 10,
                'timeoutSeconds': 30
            }
        }]}

    def test_pod_spec_with_prometheus_config_is_generated(self):
        # Exercise
        spec = domain.build_juju_pod_spec(
            app_name=self.mock_app_name,
            charm_config=self.mock_config,
            image_meta=self.mock_image_meta,
            prometheus_server_details=self.mock_prometheus_server_details)

        # Assertions
        assert type(spec) == dict
        prom_host = self.mock_prometheus_server_details.host
        prom_port = self.mock_prometheus_server_details.port
        assert spec == {'containers': [{
            'name': self.mock_app_name,
            'imageDetails': {
                'imagePath': self.mock_image_meta.image_path,
                'username': self.mock_image_meta.repo_username,
                'password': self.mock_image_meta.repo_password
            },
            'ports': [{
                'containerPort': self.mock_advertised_port,
                'protocol': 'TCP'
            }],
            'readinessProbe': {
                'httpGet': {
                    'path': '/api/health',
                    'port': self.mock_advertised_port
                },
                'initialDelaySeconds': 10,
                'timeoutSeconds': 30
            },
            'files': [{
                'name': 'prometheus-ds',
                'mountPath': '/etc/grafana/provisioning/datasources',
                'files': {
                    'prometheus.yaml': textwrap.dedent(f"""
                         apiVersion: 1

                         datasources:
                         - name: Prometheus
                           type: prometheus
                           access: proxy
                           url: http://{prom_host}:{prom_port}
                           isDefault: true
                           editable: false
                    """)
                }
            }]
        }]}

    def test_pod_spec_with_mysql_config_is_generated(self):
        # Exercise
        spec = domain.build_juju_pod_spec(
            app_name=self.mock_app_name,
            charm_config=self.mock_config,
            image_meta=self.mock_image_meta,
            mysql_server_details=self.mock_mysql_server_details)

        # Assertions
        assert type(spec) == dict
        assert spec == {'containers': [{
            'name': self.mock_app_name,
            'imageDetails': {
                'imagePath': self.mock_image_meta.image_path,
                'username': self.mock_image_meta.repo_username,
                'password': self.mock_image_meta.repo_password
            },
            'ports': [{
                'containerPort': self.mock_advertised_port,
                'protocol': 'TCP'
            }],
            'readinessProbe': {
                'httpGet': {
                    'path': '/api/health',
                    'port': self.mock_advertised_port
                },
                'initialDelaySeconds': 10,
                'timeoutSeconds': 30
            },
            'files': [{
                'name': 'mysql-db-config',
                'mountPath': '/etc/grafana',
                'files': {
                    'grafana.ini': textwrap.dedent(f"""
                        [database]
                        type = mysql
                        host = {self.mock_mysql_server_details.address}
                        name = {self.mock_mysql_server_details.database}
                        user = {self.mock_mysql_server_details.username}
                        password = {self.mock_mysql_server_details.password}

                        ;ca_cert_path =
                        ;client_key_path =
                        ;client_cert_path =
                        ;server_cert_name =
                        # Max idle conn setting default is 2
                        ;max_idle_conn = 2

                        # Max conn setting default is 0 (mean not set)
                        ;max_open_conn =

                        # Connection Max Lifetime default is 14400
                        # (means 14400 seconds or 4 hours)
                        ;conn_max_lifetime = 14400

                        # Set to true to log the sql calls and execution times.
                        ;log_queries =
                        """)
                }
            }]
        }]}

    def test_pod_spec_with_mysql_and_prometheus_config_is_generated(self):
        # Exercise
        spec = domain.build_juju_pod_spec(
            app_name=self.mock_app_name,
            charm_config=self.mock_config,
            image_meta=self.mock_image_meta,
            prometheus_server_details=self.mock_prometheus_server_details,
            mysql_server_details=self.mock_mysql_server_details)

        # Assertions
        assert type(spec) == dict
        prom_host = self.mock_prometheus_server_details.host
        prom_port = self.mock_prometheus_server_details.port
        assert spec == {'containers': [{
            'name': self.mock_app_name,
            'imageDetails': {
                'imagePath': self.mock_image_meta.image_path,
                'username': self.mock_image_meta.repo_username,
                'password': self.mock_image_meta.repo_password
            },
            'ports': [{
                'containerPort': self.mock_advertised_port,
                'protocol': 'TCP'
            }],
            'readinessProbe': {
                'httpGet': {
                    'path': '/api/health',
                    'port': self.mock_advertised_port
                },
                'initialDelaySeconds': 10,
                'timeoutSeconds': 30
            },
            'files': [{
                'name': 'prometheus-ds',
                'mountPath': '/etc/grafana/provisioning/datasources',
                'files': {
                    'prometheus.yaml': textwrap.dedent(f"""
                         apiVersion: 1

                         datasources:
                         - name: Prometheus
                           type: prometheus
                           access: proxy
                           url: http://{prom_host}:{prom_port}
                           isDefault: true
                           editable: false
                    """)
                }
            }, {
                'name': 'mysql-db-config',
                'mountPath': '/etc/grafana',
                'files': {
                    'grafana.ini': textwrap.dedent(f"""
                        [database]
                        type = mysql
                        host = {self.mock_mysql_server_details.address}
                        name = {self.mock_mysql_server_details.database}
                        user = {self.mock_mysql_server_details.username}
                        password = {self.mock_mysql_server_details.password}

                        ;ca_cert_path =
                        ;client_key_path =
                        ;client_cert_path =
                        ;server_cert_name =
                        # Max idle conn setting default is 2
                        ;max_idle_conn = 2

                        # Max conn setting default is 0 (mean not set)
                        ;max_open_conn =

                        # Connection Max Lifetime default is 14400
                        # (means 14400 seconds or 4 hours)
                        ;conn_max_lifetime = 14400

                        # Set to true to log the sql calls and execution times.
                        ;log_queries =
                        """)
                }
            }]
        }]}
