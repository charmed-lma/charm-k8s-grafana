Juju Charm/Operator for Grafana on Kubernetes
=============================================

CI Badges
---------

Click on each badge for more details.

| Branch | Build Status | Coverage |
|--------|--------------|----------|
| master | [![Build Status (master)](https://travis-ci.org/relaxdiego/charm-k8s-grafana.svg?branch=master)](https://travis-ci.org/relaxdiego/charm-k8s-grafana) | [![Coverage Status](https://coveralls.io/repos/github/relaxdiego/charm-k8s-grafana/badge.svg?branch=master)](https://coveralls.io/github/relaxdiego/charm-k8s-grafana?branch=master) |


Quick Start
-----------


```
git submodule update --init --recursive
sudo snap install juju --classic
sudo snap install microk8s --classic
sudo microk8s.enable dns dashboard registry storage
sudo usermod -a -G microk8s $(whoami)
```

Log out then log back in so that the new group membership is applied to
your shell session.

```
juju bootstrap microk8s mk8s
```

Optional: Grab coffee/beer/tea or do a 5k run. Once the above is done, do:

```
juju create-storage-pool operator-storage kubernetes storage-class=microk8s-hostpath
juju add-model lma
juju deploy . --resource grafana-image=grafana/grafana:latest
```

Wait until `juju status` shows that the charm-k8s-grafana app has
a status of active.


Preview the GUI
---------------

Run:

    kubectl -n lma port-forward svc/charm-k8s-grafana 3000:3000

The above assumes you're using the default value for `advertised-port`. If
you customized this value from 3000 to some other value, change the command
above accordingly.

Now browse to http://localhost:3000/

For more info on getting started with Grafana see [its official getting
started guide](https://prometheus.io/docs/visualization/grafana/).


Use Prometheus as a Datasource
------------------------------

Follow the steps for [deploying charm-k8s-prometheus](https://github.com/relaxdiego/charm-k8s-prometheus).
Once Prometheus is up and running, relate it with Grafana by running the
following command:

```
juju relate charm-k8s-grafana charm-k8s-prometheus
```

Once Grafana has settled, head back to the Grafana UI to see the
Prometheus datasource configured. Create a new dashboard and run
the following query to test the connection:

```
rate(prometheus_tsdb_head_chunks_created_total[1m])
```


Running the Unit Tests on Your Workstation
------------------------------------------

To run the test using the default interpreter as configured in `tox.ini`, run:

    tox

If you want to specify an interpreter that's present in your workstation, you
may run it with:

    tox -e py37

To view the coverage report that gets generated after running the tests above,
run:

    make coverage-server

The above command should output the port on your workstation where the server is
listening on. If you are running the above command on [Multipass](https://multipass.io),
first get the Ubuntu VM's IP via `multipass list` and then browse to that IP and
the abovementioned port.

NOTE: You can leave that static server running in one session while you continue
to execute `tox` on another session. That server will pick up any new changes to
the report automatically so you don't have to restart it each time.


Relying on More Comprehensive Unit Tests
----------------------------------------

To ensure that this charm is tested on the widest number of platforms possible,
we make use of Travis CI which also automatically reports the coverage report
to a publicly available Coveralls.io page. To get a view of what the state of
each relevant branch is, click on the appropriate badges found at the top of
this README.


References
----------

1. [Grafana Docker Image Configuration](https://grafana.com/docs/grafana/latest/installation/docker/)

Much of how this charm is architected is guided by the following classic
references. It will do well for future contributors to read and take them to heart:

1. [Hexagonal Architecture](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software)) by Alistair Cockburn
1. [Boundaries (Video)](https://pyvideo.org/pycon-us-2013/boundaries.html) by Gary Bernhardt
1. [Domain Driven Design (Book)](https://dddcommunity.org/book/evans_2003/) by Eric Evans
