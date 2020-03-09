from types import SimpleNamespace
import textwrap

import sys
sys.path.append('lib')

from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)
from k8s import (
    PodStatus,
)
from resources import (
    ResourceError,
)


def _create_output_obj(dict_obj):
    return SimpleNamespace(**dict_obj)


# There's a lot of code duplication here but that's fine for the meantime.
# With the tests around we can refactor these without anxiety.
def on_prometheus_available(
        server_details,
        app_name,
        config,
        image_resource):
    """Generates the k8s spec needed to deploy configure Grafana to use
    Prometheus as a datasource

    :param str app_name: The name of the application.

    :param dict config: Key-value pairs derived from config options declared
        in config.yaml

    :param OCIImageResource image_resource: Image resource object containing
        the registry path, username, and password.

    :returns: An object containing the spec dict and other attributes.

    :rtype: :class:`handlers.OnPrometheusAvailableOutput`

    """
    try:
        image_resource.fetch()
    except ResourceError as err:
        output = dict(
            unit_status=err.status,
            spec=None
        )
        return _create_output_obj(output)

    advertised_port = config['advertised-port']
    ds_path = '/etc/grafana/provisioning/datasources'
    prom_host = server_details.host
    prom_port = server_details.port

    output = dict(
        unit_status=MaintenanceStatus(
            f'Connecting to prometheus at '
            f'{prom_host}:{prom_port}'),
        spec={
            'containers': [{
                'name': app_name,
                'imageDetails': {
                    'imagePath': image_resource.image_path,
                    'username': image_resource.username,
                    'password': image_resource.password
                },
                'ports': [{
                    'containerPort': advertised_port,
                    'protocol': 'TCP'
                }],
                'readinessProbe': {
                    'httpGet': {
                        'path': '/api/health',
                        'port': advertised_port
                    },
                    'initialDelaySeconds': 10,
                    'timeoutSeconds': 30
                },
                'files': [{
                    # Note: 'name' must comply with DNS-1123 standard
                    'name': 'prometheus-ds',
                    'mountPath': f'{ds_path}',
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
            }]
        }
    )

    return _create_output_obj(output)


def on_start(event,
             app_name,
             config,
             image_resource):
    """Generates the k8s spec needed to deploy Grafana on k8s

    :param: :class:`ops.framework.EventBase` event: The event that triggered
        the calling handler.

    :param str app_name: The name of the application.

    :param dict config: Key-value pairs derived from config options declared
        in config.yaml

    :param OCIImageResource image_resource: Image resource object containing
        the registry path, username, and password.

    :returns: An object containing the spec dict and other attributes.

    :rtype: :class:`handlers.OnStartHandlerOutput`

    """
    try:
        image_resource.fetch()
    except ResourceError as err:
        output = dict(
            unit_status=err.status,
            spec=None
        )
        return _create_output_obj(output)

    advertised_port = config['advertised-port']

    output = dict(
        unit_status=MaintenanceStatus("Configuring pod"),
        spec={
            'containers': [{
                'name': app_name,
                'imageDetails': {
                    'imagePath': image_resource.image_path,
                    'username': image_resource.username,
                    'password': image_resource.password
                },
                'ports': [{
                    'containerPort': advertised_port,
                    'protocol': 'TCP'
                }],
                'readinessProbe': {
                    'httpGet': {
                        'path': '/api/health',
                        'port': advertised_port
                    },
                    'initialDelaySeconds': 10,
                    'timeoutSeconds': 30
                }
            }]
        }
    )

    return _create_output_obj(output)


def on_config_changed(event, app_name):

    pod_status = PodStatus(app_name=app_name)
    pod_status.fetch()

    pod_is_ready = False

    if pod_status.is_unknown:
        unit_status = MaintenanceStatus("Waiting for pod to appear")
    elif not pod_status.is_running:
        unit_status = MaintenanceStatus("Pod is starting")
    elif pod_status.is_running and not pod_status.is_ready:
        unit_status = MaintenanceStatus("Pod is getting ready")
    elif pod_status.is_running and pod_status.is_ready:
        unit_status = ActiveStatus()
        pod_is_ready = True

    return SimpleNamespace(**dict(
        unit_status=unit_status,
        pod_is_ready=pod_is_ready
    ))
