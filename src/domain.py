import textwrap
import sys
sys.path.append('lib')

from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)


# DOMAIN SERVICES

# More stateless functions. This group is purely business logic that take
# simple values or data structures and produce new values from them.

def build_juju_pod_spec(app_name,
                        charm_config,
                        image_meta,
                        prometheus_server_details=None):
    advertised_port = charm_config['advertised-port']

    spec = {
        'containers': [{
            'name': app_name,
            'imageDetails': {
                'imagePath': image_meta.image_path,
                'username': image_meta.repo_username,
                'password': image_meta.repo_password
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

    if prometheus_server_details:
        ds_path = '/etc/grafana/provisioning/datasources'
        prom_host = prometheus_server_details.host
        prom_port = prometheus_server_details.port

        spec['containers'][0]['files'] = [{
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

    return spec


def build_juju_unit_status(pod_status):
    if pod_status.is_unknown:
        unit_status = MaintenanceStatus("Waiting for pod to appear")
    elif not pod_status.is_running:
        unit_status = MaintenanceStatus("Pod is starting")
    elif pod_status.is_running and not pod_status.is_ready:
        unit_status = MaintenanceStatus("Pod is getting ready")
    elif pod_status.is_running and pod_status.is_ready:
        unit_status = ActiveStatus()

    return unit_status
