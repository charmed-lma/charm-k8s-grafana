#!/usr/bin/env python3
import os
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

from adapters import (
    k8s,
    resources,
)
import interface_http
from domain import (
    build_juju_pod_spec,
    build_juju_unit_status,
)


class Charm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)

        self.prometheus_client = interface_http.Client(self, 'prometheus-api')

        # Bind event handlers to events
        event_handler_bindings = {
            self.on.start: self.on_start,
            self.on.config_changed: self.on_config_changed,
            self.on.upgrade_charm: self.on_start,
            self.prometheus_client.on.server_available: self.on_prom_available
        }
        for event, delegator in event_handler_bindings.items():
            self.framework.observe(event, delegator)

    # HANDLERS

    def on_config_changed(self, event):
        juju_model = os.environ["JUJU_MODEL_NAME"]
        juju_app = self.framework.model.app.name
        juju_unit = os.environ["JUJU_UNIT_NAME"]

        pod_is_ready = False

        while not pod_is_ready:
            k8s_pod_status = k8s.get_pod_status(
                juju_model=juju_model,
                juju_app=juju_app,
                juju_unit=juju_unit
            )
            juju_unit_status = build_juju_unit_status(k8s_pod_status)
            self.framework.model.unit.status = juju_unit_status
            pod_is_ready = isinstance(juju_unit_status, ActiveStatus)

    def on_prom_available(self, event):
        if not self.framework.model.unit.is_leader():
            return

        app_name = self.framework.model.app.name
        charm_config = self.framework.model.config
        image_name = 'grafana-image',
        image_meta_path = self.framework.model.resources.fetch(image_name)

        image_meta = resources.get_image_meta(image_name, image_meta_path)

        juju_pod_spec = build_juju_pod_spec(
            app_name=app_name,
            charm_config=charm_config,
            image_meta=image_meta,
            prometheus_server_details=event.server_details,
        )

        self.framework.model.pod.set_spec(juju_pod_spec)
        self.framework.model.unit.status = MaintenanceStatus("Configuring pod")

    def on_start(self, event):
        pass


if __name__ == "__main__":
    main(Charm)
