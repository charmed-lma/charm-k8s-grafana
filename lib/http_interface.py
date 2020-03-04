import json
import sys
sys.path.append('lib')

from ops.framework import (
    EventBase,
    EventSource,
    EventsBase,
    Object,
)


#
# Server
#

class NewClientEvent(EventBase):

    def __init__(self, handle, server_details):
        super().__init__(handle)
        self._server_details = server_details

    @property
    def server_details(self):
        return self._server_details

    def snapshot(self):
        return {
            'type': str(type(self.server_details)),
            'host': self.server_details.host,
            'port': self.server_details.port,
        }

    def restore(self, snapshot):
        relation = self.model.get_relation(snapshot['relation_name'],
                                           snapshot['relation_id'])
        unit = self.model.unit
        self._server_details = ServerDetails(relation, unit, **{
            k: v for k, v in snapshot.items()
            if k in ['host', 'port']
        })


class ServerDetails:

    def __init__(self, relation, local_unit, host=None, port=None):
        self._relation = relation
        self._local_unit = local_unit
        self.set_address(host, port)

    def set_address(self, host, port):
        self._host = host
        self._port = port
        self._relation.data[self._local_unit]['extended_data'] = json.dumps([{
            'hostname': host,
            'port': port,
        }])

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port


class ServerEvents(EventsBase):
    new_client = EventSource(NewClientEvent)


class Server(Object):
    on = ServerEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)

        self.framework.observe(charm.on[relation_name].relation_joined,
                               self.on_joined)

    def on_joined(self, event):
        self.on.new_client.emit(ServerDetails(event.relation,
                                              self.model.unit))


#
# Client
#

class ServerAvailableEvent(EventBase):

    def __init__(self, handle, server_details):
        super().__init__(handle)
        self._server_details = server_details

    @property
    def server_details(self):
        return self._server_details

    def snapshot(self):
        return {
            'type': str(type(self.server_details)),
            'host': self.server_details.host,
            'port': self.server_details.port,
        }

    def restore(self, snapshot):
        self._server_details = ServerDetails(**{
            k: v for k, v in snapshot.items()
            if k in ['host', 'port']
        })


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
        relation = self.framework.model.relations[self.relation_name][0]
        server_details = {}

        for app_or_unit in [relation.app] + list(relation.units):
            data = relation.data[app_or_unit]
            # if all(data.get(key) for key in ('host', 'port')):
            #     server_details = data
            server_details.update({app_or_unit: str(dict(data))})
        # # This produces an empty dict
        # data = {
        #     k: v for k, v in relation.data.items()
        #     if k in ['host', 'port']
        # }

        # server_details = ServerDetails(host=str(server_details))
        server_details = str(server_details)
        self.on.server_available.emit(server_details)
