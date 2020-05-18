import random
import sys
import unittest
from unittest.mock import (
    # call,
    patch,
)
from uuid import uuid4

sys.path.append('lib')

from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)
from ops.testing import (
    Harness,
)

sys.path.append('src')
import charm
from adapters.k8s import (
    ServiceSpec
)
# from interface_http import (
#     ServerDetails,
# )


class CharmTest(unittest.TestCase):

    @patch('charm.os', spec_set=True, autospec=True)
    @patch('charm.k8s', spec_set=True, autospec=True)
    @patch('charm.build_juju_unit_status', spec_set=True, autospec=True)
    def test__on_config_changed__sets_the_unit_status_correctly(
        self,
        mock_build_juju_unit_status_func,
        mock_k8s_mod,
        mock_os_mod,
    ):
        # Setup
        harness = Harness(charm.Charm)
        harness.begin()

        mock_juju_unit_states = [
            MaintenanceStatus(str(uuid4())),
            MaintenanceStatus(str(uuid4())),
            ActiveStatus(str(uuid4())),
        ]
        mock_build_juju_unit_status_func.side_effect = mock_juju_unit_states

        # Exercise
        harness.update_config()

        # Assert
        self.assertEqual(harness.model.unit.status, mock_juju_unit_states[-1])
        # Not ideal but we use this mock as a proxy for asserting whether
        # on_config_changed set the unit status 3 times
        self.assertEqual(mock_build_juju_unit_status_func.call_count,
                         len(mock_juju_unit_states))

    @patch('charm.interface_http.os', spec_set=True, autospec=True)
    @patch('charm.interface_http.k8s', spec_set=True, autospec=True)
    @patch('charm.build_juju_pod_spec', spec_set=True, autospec=True)
    @patch('charm.resources', spec_set=True, autospec=True)
    def test__on_prom_available__it_updates_the_juju_pod_spec(
        self,
        mock_resources_mod,
        mock_build_juju_pod_spec_func,
        mock_k8s_mod,
        mock_os_mod,
    ):
        # Setup
        mock_service_spec = ServiceSpec({
            "kind": "Service",
            "apiVersion": "v1",
            "metadata": {
                "name": "charm-k8s-prometheus",
                "namespace": "lma",
                "uid": "5e5684e0-5870-450e-ab9d-ff840e0b10fb",
                "resourceVersion": "257015",
                "creationTimestamp": "2020-02-21T06:40:34Z",
                "labels": {
                    "juju-app": "charm-k8s-prometheus"
                },
                "annotations": {
                    "juju.io/model": "d3fb103b-515e-42c8-87f8-5ff26dd7a1e9"
                }
            },
            "spec": {
                "ports": [
                    {
                        "protocol": "TCP",
                        "port": random.randint(1, 65535),
                        "targetPort": random.randint(1, 65535)
                    }
                ],
                "selector": {
                    "juju-app": "charm-k8s-prometheus"
                },
                "clusterIP": str(uuid4()),
                "type": "ClusterIP",
                "sessionAffinity": "None"
            },
            "status": {
                "loadBalancer": {
                }
            }
        })
        mock_k8s_mod.get_service_spec.return_value = mock_service_spec
        # mock_server_details = ServerDetails(host=mock_service_spec.host,
        #                                     port=mock_service_spec.port)

        harness = Harness(charm.Charm)
        harness.begin()

        # Exercise
        harness.set_leader()
        relation_id = harness.add_relation('prometheus-api', 'prometheus')
        harness.add_relation_unit(relation_id, 'prometheus/0')
        harness.update_relation_data(relation_id,
                                     'prometheus/0',
                                     {'key1': 'val1'})

        # # Assert
        self.assertEqual(mock_build_juju_pod_spec_func.call_count, 1)

        args, kwargs = mock_build_juju_pod_spec_func.call_args
        self.assertEqual(kwargs['app_name'],
                         harness.framework.model.app.name)
        self.assertEqual(kwargs['charm_config'],
                         harness.framework.model.config)
        self.assertEqual(kwargs['image_meta'],
                         mock_resources_mod.get_image_meta.return_value)
        # assert mock_build_juju_pod_spec_func.call_args == \
        #     call(app_name=harness.framework.model.app.name,
        #          charm_config=harness.framework.model.config,
        #          image_meta=mock_service_spec,
        #          prometheus_server_details=mock_server_details)
        #
        # assert mock_fw.set_pod_spec.call_count == 1
        # assert mock_fw.set_pod_spec.call_args == \
        #     call(mock_build_juju_pod_spec_func.return_value)
        #
        # assert mock_fw.set_unit_status.call_count == 1
        # args, kwargs = mock_fw.set_unit_status.call_args_list[0]
        # assert type(args[0]) == MaintenanceStatus


# class OnStartHandlerTest(unittest.TestCase):
#
#     @patch('charm.build_juju_pod_spec', spec_set=True, autospec=True)
#     def test__it_updates_the_juju_pod_spec(self,
#                                            mock_build_juju_pod_spec_func):
#         # Setup
#         mock_fw_adapter_cls = \
#             create_autospec(adapters.framework.FrameworkAdapter,
#                             spec_set=True)
#         mock_fw = mock_fw_adapter_cls.return_value
#         mock_fw.am_i_leader.return_value = True
#
#         mock_event_cls = create_autospec(EventBase, spec_set=True)
#         mock_event = mock_event_cls.return_value
#
#         # Exercise
#         charm.on_start_handler(mock_event, mock_fw)
#
#         # Assert
#         assert mock_build_juju_pod_spec_func.call_count == 1
#         assert mock_build_juju_pod_spec_func.call_args == \
#             call(app_name=mock_fw.get_app_name.return_value,
#                  charm_config=mock_fw.get_config.return_value,
#                  image_meta=mock_fw.get_image_meta.return_value)
#
#         assert mock_fw.set_pod_spec.call_count == 1
#         assert mock_fw.set_pod_spec.call_args == \
#             call(mock_build_juju_pod_spec_func.return_value)
#
#         assert mock_fw.set_unit_status.call_count == 1
#         args, kwargs = mock_fw.set_unit_status.call_args_list[0]
#         assert type(args[0]) == MaintenanceStatus
