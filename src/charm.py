#!/usr/bin/env python3
import sys
sys.path.append('lib')

from ops.charm import (
    CharmBase,
)
from ops.main import main
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)

from interface_http import interface_http

from adapters import (
    framework,
    k8s,
)

from domain import (
    build_juju_pod_spec,
    build_juju_unit_status,
)


# CHARM

# This charm class mainly does self-configuration via its initializer and
# contains not much logic. It also just has one-liner delegators the design
# of which is further discussed below (just before the delegator definitions)

class Charm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)

        self.adapter = framework.FrameworkAdapter(self.framework)
        self.prometheus_client = interface_http.Client(self, 'prometheus-api')

        event_delegators = {
            self.on.start: self.on_start,
            self.on.config_changed: self.on_config_changed,
            self.on.upgrade_charm: self.on_start,
            self.prometheus_client.on.server_available: self.on_prom_available
        }
        for event, delegator in event_delegators.items():
            self.adapter.observe(event, delegator)

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
        on_config_changed_handler(event, self.adapter)

    def on_prom_available(self, event):
        on_prom_available_handler(event, self.adapter)

    def on_start(self, event):
        on_start_handler(event, self.adapter)


# EVENT HANDLERS

# These event handlers are designed to be stateless and, as much as possible,
# procedural (run from top to bottom). They are stateless since these stored
# states are already handled by the Charm object anyway and also because this
# simplifies testing of said handlers. They are also procedural since they are
# similar to controllers in an MVC app in that they are only concerned with
# coordinating domain models and services.

def on_config_changed_handler(event, framework):
    juju_model = framework.get_model_name()
    juju_app = framework.get_app_name()
    juju_unit = framework.get_unit_name()

    pod_is_ready = False

    while not pod_is_ready:
        k8s_pod_status = k8s.get_pod_status(juju_model=juju_model,
                                            juju_app=juju_app,
                                            juju_unit=juju_unit)
        juju_unit_status = build_juju_unit_status(k8s_pod_status)
        framework.set_unit_status(juju_unit_status)
        pod_is_ready = isinstance(juju_unit_status, ActiveStatus)


def on_prom_available_handler(event, framework):
    if not framework.am_i_leader():
        return

    juju_pod_spec = build_juju_pod_spec(
        app_name=framework.get_app_name(),
        charm_config=framework.get_config(),
        image_meta=framework.get_image_meta('grafana-image'),
        prometheus_server_details=event.server_details,
    )

    framework.set_pod_spec(juju_pod_spec)
    framework.set_unit_status(MaintenanceStatus("Configuring pod"))


def on_start_handler(event, framework):
    if not framework.am_i_leader():
        return

    juju_pod_spec = build_juju_pod_spec(
        app_name=framework.get_app_name(),
        charm_config=framework.get_config(),
        image_meta=framework.get_image_meta('grafana-image'),
    )

    framework.set_pod_spec(juju_pod_spec)
    framework.set_unit_status(MaintenanceStatus("Configuring pod"))


if __name__ == "__main__":
    main(Charm)
