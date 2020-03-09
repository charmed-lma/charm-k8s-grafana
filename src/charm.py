#!/usr/bin/env python3
import logging
logger = logging.getLogger()
import sys
sys.path.append('lib')

from ops.charm import (
    CharmBase,
)
from ops.main import main
import http_interface

from adapters import FrameworkAdapter
from resources import (
    GrafanaImageResource,
)
import handlers


class Charm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)

        # Abstract out framework and friends so that this object is not
        # too tightly coupled with the underlying framework's implementation.
        # From this point forward, our Charm object will only interact with the
        # adapter and not directly with the framework.
        self.adapter = FrameworkAdapter(self.framework)

        self.prometheus_client = http_interface.Client(self, 'prometheus-api')

        # Bind event handlers to events
        event_handler_bindings = {
            self.on.start: self.on_start_delegator,
            self.on.config_changed: self.on_config_changed_delegator,
            self.on.upgrade_charm: self.on_upgrade_delegator,
            self.prometheus_client.on.server_available:
                self.on_prometheus_available_delegator,
        }
        for event, handler in event_handler_bindings.items():
            self.adapter.observe(event, handler)

        self.image_resource = GrafanaImageResource(
            resources_repo=self.adapter.get_resources_repo()
        )

    def on_start_delegator(self, event):
        if self.adapter.check_if_i_am_leader():
            logging.info(f'Configuring pod')
            output = handlers.on_start(
                event=event,
                app_name=self.adapter.get_app_name(),
                config=self.adapter.get_config(),
                image_resource=self.image_resource,
            )
            self.adapter.set_pod_spec(output.spec)
            self.adapter.set_unit_status(output.unit_status)
        else:
            logging.info(f'Unit is not a leader. Skipping pod config')

    def on_config_changed_delegator(self, event):
        pod_is_ready = False
        app_name = self.adapter.get_app_name()

        logging.info(f'Waiting for k8s pod to be ready')

        while not pod_is_ready:
            output = handlers.on_config_changed(
                event=event,
                app_name=app_name
            )
            self.adapter.set_unit_status(output.unit_status)
            pod_is_ready = output.pod_is_ready

        logging.info(f'Ready to serve requests')

    def on_prometheus_available_delegator(self, event):
        app_name = self.adapter.get_app_name()
        if self.adapter.check_if_i_am_leader():
            logging.info(f'Adding prometheus datasource')
            output = handlers.on_prometheus_available(
                server_details=event.server_details,
                app_name=app_name,
                config=self.adapter.get_config(),
                image_resource=self.image_resource,
            )
            self.adapter.set_pod_spec(output.spec)
            self.adapter.set_unit_status(output.unit_status)
        else:
            logging.info(f'Unit is not a leader. Skipping prometheus config')

    def on_upgrade_delegator(self, event):
        logging.info(f'on_upgrade_delegator called')
        self.on_start_delegator(event)


if __name__ == "__main__":
    main(Charm)
