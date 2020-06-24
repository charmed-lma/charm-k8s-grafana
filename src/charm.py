#!/usr/bin/env python3
from collections import namedtuple
import sys
import yaml
sys.path.append('lib')

from ops.charm import (
    CharmBase,
)
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
    MaintenanceStatus,
    ModelError,
)

import interface_http

from adapters import (
    framework,
    k8s,
)

from domain import (
    build_juju_pod_spec,
    build_juju_unit_status,
)


# ERRORS

class ResourceError(ModelError):

    def __init__(self, resource_name, message):
        super().__init__(resource_name)
        self.status = BlockedStatus(f'{resource_name}: {message}')


# MODELS

ImageMeta = namedtuple('ImageMeta', 'image_path repo_username repo_password')


# CHARM

# This charm class mainly does self-configuration via its initializer and
# contains not much logic. It also just has one-liner delegators the design
# of which is further discussed below (just before the delegator definitions)

class Charm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)

        # Abstract out framework and friends so that this object is not
        # too tightly coupled with the underlying framework's implementation.
        # From this point forward, our Charm object will only interact with the
        # adapter and not directly with the framework.
        self.fw_adapter = framework.FrameworkAdapter(self.framework)
        self.prometheus_client = interface_http.Client(self, 'prometheus-api')

        # Bind event handlers to events
        event_handler_bindings = {
            self.on.start: self.on_start,
            self.on.config_changed: self.on_config_changed,
            self.on.upgrade_charm: self.on_start,
            self.prometheus_client.on.server_available: self.on_prom_available
        }
        for event, delegator in event_handler_bindings.items():
            self.fw_adapter.observe(event, delegator)

    # DELEGATORS

    # These delegators exist to decouple the actual handlers from the
    # underlying framework which has some very specific requirements that
    # do not always apply to every event. For example, because we have to
    # instantiate the interface_http.Client during charm initialization,
    # we are forced to write unit tests that mock out that object even
    # for handlers that do not need it. This hard coupling results in verbose
    # tests that contain unused mocks. These tests tend to be hard to follow
    # so to counter that, the logic is moved away from this class.

    def on_config_changed(self, event):
        on_config_changed_handler(event, self.fw_adapter)

    def on_prom_available(self, event):
        on_prom_available_handler(event, self.fw_adapter)

    def on_start(self, event):
        on_start_handler(event, self.framework)


# EVENT HANDLERS

# These event handlers are designed to be stateless and, as much as possible,
# procedural (run from top to bottom). They are stateless since these stored
# states are already handled by the Charm object anyway and also because this
# simplifies testing of said handlers. They are also procedural since they are
# similar to controllers in an MVC app in that they are only concerned with
# coordinating domain models and services.

def on_config_changed_handler(event, fw_adapter):
    juju_model = fw_adapter.get_model_name()
    juju_app = fw_adapter.get_app_name()
    juju_unit = fw_adapter.get_unit_name()

    pod_is_ready = False

    while not pod_is_ready:
        k8s_pod_status = k8s.get_pod_status(juju_model=juju_model,
                                            juju_app=juju_app,
                                            juju_unit=juju_unit)
        juju_unit_status = build_juju_unit_status(k8s_pod_status)
        fw_adapter.set_unit_status(juju_unit_status)
        pod_is_ready = isinstance(juju_unit_status, ActiveStatus)


def on_prom_available_handler(event, fw_adapter):
    if not fw_adapter.am_i_leader():
        return

    juju_pod_spec = build_juju_pod_spec(
        app_name=fw_adapter.get_app_name(),
        charm_config=fw_adapter.get_config(),
        image_meta=fw_adapter.get_image_meta('grafana-image'),
        prometheus_server_details=event.server_details,
    )

    fw_adapter.set_pod_spec(juju_pod_spec)
    fw_adapter.set_unit_status(MaintenanceStatus("Configuring pod"))


def on_start_handler(event, framework):
    if not framework.model.unit.is_leader():
        return

    juju_pod_spec = build_juju_pod_spec(
        app_name=framework.model.app.name,
        charm_config=framework.model.config,
        image_meta=_fetch_image_meta('grafana-image',
                                     framework.model.resources),
    )

    framework.model.pod.set_spec(juju_pod_spec)
    framework.model.unit.status = MaintenanceStatus("Configuring pod")


def _fetch_image_meta(image_name, resources_repo):
    path = resources_repo.fetch(image_name)
    if not path.exists():
        raise ResourceError(image_name, f'Resource not found at {str(path)})')

    resource_yaml = path.read_text()

    if not resource_yaml:
        raise ResourceError(image_name, f'Resource unreadable at {str(path)})')

    try:
        rd = yaml.safe_load(resource_yaml)
    except yaml.error.YAMLError:
        raise ResourceError(image_name, f'Invalid YAML at {str(path)})')
    else:
        return ImageMeta(image_path=rd['registrypath'],
                         repo_username=rd['username'],
                         repo_password=rd['password'])


if __name__ == "__main__":
    main(Charm)
