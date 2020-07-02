# Ideally, this interface and its tests should be located in its own
# repository. However, to keep the initial development process simple,
# this file is colocated with its first dependent charm. It should
# be moved out eventually though.
import logging

log = logging.getLogger()

from ops.framework import (
    EventSource,
    Object,
    ObjectEvents,
)
from ops.framework import EventBase


class MySQLServerDetails:

    def __init__(self, data_dict):
        log.debug("Initializing with data {}".format(data_dict))
        self._data_dict = data_dict

    @property
    def address(self):
        host = self._data_dict.get('ingress-address', self._data_dict['host'])
        port = self._data_dict.get('port', 3306)
        return "{}:{}".format(host, port)

    @property
    def database(self):
        return self._data_dict['database']

    @property
    def username(self):
        return self._data_dict['user']

    @property
    def password(self):
        return self._data_dict['password']

    # Serialization and de-serialization methods

    def snapshot(self):
        log.debug("Returning snapshot {}".format(self._data_dict))
        return self._data_dict

    @classmethod
    def restore(cls, snapshot):
        log.debug("Restoring from snapshot: {}".format(snapshot))
        if snapshot:
            return cls(snapshot)
        else:
            return None


class NewMySQLRelationEvent(EventBase):

    # server_details here is explicitly provided to the `emit()` call inside
    # `Client.on_relation_changed` below. `handle` on the other hand is
    # automatically provided by `emit()`
    def __init__(self, handle, server_details):
        super().__init__(handle)
        self._server_details = server_details

    @property
    def server_details(self):
        return self._server_details

    # The Operator Framework will serialize and deserialize this event object
    # as it passes it to the charm. The following snapshot and restore methods
    # ensure that our underlying data don't get lost along the way.

    def snapshot(self):
        log.debug("Calling snapshot of server_details")
        return self.server_details.snapshot()

    def restore(self, snapshot):
        log.debug("Restoring snapshot of server_details")
        self._server_details = MySQLServerDetails.restore(snapshot)


class MySQLRelationEvents(ObjectEvents):
    new_relation = EventSource(NewMySQLRelationEvent)


class MySQLInterface(Object):
    on = MySQLRelationEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)

        self._relation_name = relation_name

        self.framework.observe(charm.on[relation_name].relation_changed,
                               self.on_relation_changed)

    @property
    def relation_name(self):
        return self._relation_name

    def on_relation_changed(self, event):
        log.debug(
            "Receiving relation data from remote unit {}".format(event.unit))
        remote_data = event.relation.data[event.unit]
        log.debug(
            "Received remote_data: {}".format(dict(remote_data))
        )

        log.debug("Initializing MySQLServerDetails object "
                  "from remote data")
        server_details = MySQLServerDetails(dict(remote_data))

        log.debug("Emitting event {}".format(self.on.new_relation))
        self.on.new_relation.emit(server_details)
