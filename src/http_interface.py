import sys
sys.path.append('lib')

from ops.framework import (
    EventBase,
    EventSource,
    EventsBase,
    Object,
)

from k8s import (
    ServiceSpec,
)


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


#
# Server
#

class NewClientEvent(EventBase):

    def __init__(self, handle, relation):
        super().__init__(handle)
        self._server_details = "NewClientEvent"

    @property
    def server_details(self):
        return self._server_details

    def snapshot(self):
        return {
            'server_details': self.server_details
        }

    def restore(self, snapshot):
        self._server_details = snapshot['server_details']


class ServerEvents(EventsBase):
    new_client = EventSource(NewClientEvent)


class Server(Object):
    on = ServerEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)

        self.framework.observe(charm.on[relation_name].relation_joined,
                               self.on_joined)

    def on_joined(self, event):
        self.on.new_client.emit("emmitted param")


#
# Client
#

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
        return {
            'server_details_host': self.server_details.host,
            'server_details_port': self.server_details.port,
        }

    def restore(self, snapshot):
        self._server_details = \
            ServerDetails(host=snapshot['server_details_host'],
                          port=snapshot['server_details_port'])


class ClientEvents(EventsBase):
    server_available = EventSource(ServerAvailableEvent)


class Client(Object):
    on = ClientEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)

        self._relation_name = relation_name

        self.framework.observe(charm.on[relation_name].relation_changed,
                               self.on_relation_changed)

    @property
    def relation_name(self):
        return self._relation_name

    def on_relation_changed(self, event):
        # TODO: Add some logic here to pick up the right relation in case
        # the client charm is related to more than one unit. E.g. when the
        # server is in HA mode.
        relation = self.framework.model.relations[self.relation_name][0]

        # Fetch the k8s Service resource fronting the server pods
        service_spec = ServiceSpec(relation.app.name)
        service_spec.fetch()

        server_details = ServerDetails(host=service_spec.host,
                                       port=service_spec.port)
        self.on.server_available.emit(server_details)
