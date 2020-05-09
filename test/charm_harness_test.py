import sys
import unittest

sys.path.append('lib')

from ops.testing import (
    Harness,
)

sys.path.append('src')

from charm import Charm


class CharmHarnessTest(unittest.TestCase):

    def test__initialize_charm_sucessfully(self):
        # Setup
        harness = Harness(Charm)

        # Exercise
        harness.begin()

        # TODO: Add assertions here

    def test__add_prometheus_relation(self):
        # Setup
        harness = Harness(Charm)
        harness.begin()

        # Exercise
        harness.add_relation('prometheus-api', 'prometheus')

        # TODO: Add assertions here
