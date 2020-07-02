import sys
import logging
sys.path.append('lib')

from ops.framework import (
    EventBase,
    EventSource,
    Object,
    ObjectEvents,
)

from adapters import framework

# Ideally, this interface and its tests should be located in its own
# repository. However, to keep the initial development process simple,
# this file is colocated with its first dependent charm. It should
# be moved out eventually though.


#
# Client/Requiring Charm Classes
# This are the classes used by the client/requiring charm
#

class ServerDetails:

    def __init__(self, host=None, port=None):
        self.set_address(host, port)

    def set_address(self, host, port):
        self._host = host
        self._port = port

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @classmethod
    def restore(cls, snapshot):
        if snapshot:
            return cls(host=snapshot['server_details.host'],
                       port=snapshot['server_details.port'])
        else:
            return None

    def snapshot(self):
        return {
            'server_details.host': self.host,
            'server_details.port': self.port,
        }


class ServerAvailableEvent(EventBase):

    # server_details here is explicitly provided to the `emit()` call inside
    # `Client.on_relation_changed` below. `handle` on the other hand is
    # automatically provided by `emit()`
    def __init__(self, handle, server_details):
        super().__init__(handle)
        self._server_details = server_details

    @property
    def server_details(self):
        return self._server_details

    def snapshot(self):
        return self.server_details.snapshot()

    def restore(self, snapshot):
        self._server_details = ServerDetails.restore(snapshot)


class ClientEvents(ObjectEvents):
    server_available = EventSource(ServerAvailableEvent)


class Client(Object):
    on = ClientEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self._relation_name = relation_name

        # Abstract out framework and friends so that this object is not
        # too tightly coupled with the underlying framework's implementation.
        # From this point forward, our Client object will only interact with
        # the adapter and not directly with the framework.
        self.adapter = framework.FrameworkAdapter(self.framework)

        self.adapter.observe(charm.on[relation_name].relation_changed,
                             self.on_relation_changed)

    @property
    def relation_name(self):
        return self._relation_name

    def on_relation_changed(self, event):
        remote_relation_data = event.relation.data[event.unit]
        logging.debug(
            "Received from Prom: %s " % list(remote_relation_data.items())
        )

        server_details = ServerDetails(
            host=remote_relation_data['ingress-address'],
            port=remote_relation_data['prometheus-port']
        )
        self.on.server_available.emit(server_details)
