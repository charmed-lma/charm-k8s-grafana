import time
from types import SimpleNamespace

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


def on_prometheus_available(server_details):
    # TODO: Do something here to reconfigure the pod and make Grafana
    #       be aware of prometheus as a data source.
    time.sleep(5)


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
