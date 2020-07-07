#!/usr/bin/env python3
import logging
import sys
sys.path.append('lib')

from ops.charm import (
    CharmBase,
)
from ops.framework import (
    StoredState,
)
from ops.main import main
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)

import interface_http
import interface_mysql

from adapters import (
    framework,
    k8s,
)

from domain import (
    build_juju_pod_spec,
    build_juju_unit_status,
)

log = logging.getLogger(__name__)


# CHARM

# This charm class mainly does self-configuration via its initializer and
# contains not much logic. It also just has one-liner delegators the design
# of which is further discussed below (just before the delegator definitions)

class Charm(CharmBase):
    state = StoredState()

    def __init__(self, *args):
        super().__init__(*args)

        self.prometheus_client = interface_http.Client(self, 'prometheus-api')
        self.mysql = interface_mysql.MySQLInterface(self, 'mysql')

        self.state.set_default(
            prometheus_server_details=None,
            mysql_server_details=None,
        )

        # Bind event handlers to events
        event_handler_bindings = {
            self.mysql.on.new_relation: self._on_mysql_new_relation,
            self.on.config_changed: self.on_config_changed,
            self.on.start: self.on_start,
            self.on.update_status: self.on_update_status,
            self.on.upgrade_charm: self.on_start,
            self.prometheus_client.on.server_available: self.on_prom_available,
        }
        for event, delegator in event_handler_bindings.items():
            self.framework.observe(event, delegator)

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
        log.debug("Received event {}".format(event))
        _on_config_changed_handler(
            model_name=self.model.name,
            app_name=self.model.app.name,
            unit_name=self.model.unit.name,
            set_unit_status_func=_get_unit_status_setter(self.framework))

    def _on_mysql_new_relation(self, event):
        log.debug("Received event {}".format(event))

        server_details = event.server_details
        log.debug("Received server_details {}:{}".format(type(server_details),
                                                         server_details))
        log.debug("Snapshotting to StoredState")
        self.state.mysql_server_details = server_details.snapshot()

        log.debug("Calling update_grafana_configuration")
        _on_server_new_relation_handler(
            event=event,
            app_name=self.model.app.name,
            unit_is_leader=self.model.unit.is_leader(),
            mysql_server_details=self.state.mysql_server_details,
            prometheus_server_details=self.state.prometheus_server_details,
            set_pod_spec_func=self.model.pod.set_spec,
            set_unit_status_func=_get_unit_status_setter(self.framework))

    def on_prom_available(self, event):
        log.debug("Received event {}".format(event))

        server_details = event.server_details
        log.debug("Received server_details {}:{}".format(type(server_details),
                                                         server_details))

        log.debug("Snapshotting to StoredState")
        self.state.prometheus_server_details = server_details.snapshot()

        log.debug("Calling update_grafana_configuration")
        on_server_new_relation_handler(event, self.state, self.fw_adapter)

    def on_start(self, event):
        on_start_handler(event, self.fw_adapter)

    def on_update_status(self, event):
        on_update_status_handler(event, self.fw_adapter)


# EVENT HANDLERS

# These event handlers are designed to be stateless and, as much as possible,
# procedural (run from top to bottom). They are stateless since these stored
# states are already handled by the Charm object anyway and also because this
# simplifies testing of said handlers. They are also procedural since they are
# similar to controllers in an MVC app in that they are only concerned with
# coordinating domain models and services.

def _on_config_changed_handler(
        model_name,
        app_name,
        unit_name,
        set_unit_status_func):
    _update_unit_status_based_on_k8s_pod_status(
        juju_model=model_name,
        juju_app=app_name,
        juju_unit=unit_name,
        set_unit_status_func=set_unit_status_func)


def _on_server_new_relation_handler(
        event,
        app_name,
        unit_is_leader,
        mysql_server_details,
        prometheus_server_details,
        set_pod_spec_func,
        set_unit_status_func):
    log.debug("Got event {}".format(event))
    if not unit_is_leader:
        return

    mysql_details = \
        interface_mysql.MySQLServerDetails.restore(mysql_server_details)
    prometheus_details = \
        interface_http.ServerDetails.restore(prometheus_server_details)

    juju_pod_spec = build_juju_pod_spec(
        app_name=app_name,
        image_meta=framework.get_image_meta('grafana-image'),
        mysql_server_details=mysql_details,
        prometheus_server_details=prometheus_details,
    )

    log.info("Updating juju podspec with new backend details")
    set_pod_spec_func(juju_pod_spec)
    set_unit_status_func(MaintenanceStatus("Configuring pod"))


def on_start_handler(event, fw_adapter):
    if not fw_adapter.am_i_leader():
        return

    juju_pod_spec = build_juju_pod_spec(
        app_name=fw_adapter.get_app_name(),
        charm_config=fw_adapter.get_config(),
        image_meta=fw_adapter.get_image_meta('grafana-image'),
    )

    fw_adapter.set_pod_spec(juju_pod_spec)
    fw_adapter.set_unit_status(MaintenanceStatus("Configuring pod"))


def on_update_status_handler(event, fw_adapter):
    log.debug("update_status event detected")
    update_unit_status(fw_adapter)


def _update_unit_status_based_on_k8s_pod_status(
        juju_model,
        juju_app,
        juju_unit,
        set_unit_status_func):

    pod_is_ready = False

    while not pod_is_ready:
        k8s_pod_status = k8s.get_pod_status(juju_model=juju_model,
                                            juju_app=juju_app,
                                            juju_unit=juju_unit)
        juju_unit_status = build_juju_unit_status(k8s_pod_status)
        set_unit_status_func(juju_unit_status)
        pod_is_ready = isinstance(juju_unit_status, ActiveStatus)


# HELPERS

def _get_unit_status_setter(framework):
    def set_unit_status(state_obj):
        framework.model.unit.status = state_obj
    return set_unit_status


if __name__ == "__main__":
    main(Charm)
