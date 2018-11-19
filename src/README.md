# Overview
Complete automation of your physical servers for amazing data centre operational efficiency. On premises, open source and supported.

# MAAS
- [MAAS Website](https://www.maas.io/)

# Usage
This charm can be used to deploy MAAS.

The charm configuration exposes an option called `maas-mode`, which is used by the charm to know what type of 
MAAS node to configure (region, rack, region+rack, or all).

In order to facilitate more complex deployments, you must configure the `maas-mode` configuration option.

The valid choices for the `maas-mode` config can be explained as follows:

* `all` - This will configure an all in one deployment, with the region, rack, and database all on the same node (no postgresql charm needed).

* `region` - This will configure the MAAS mode to `region`, the node will wait for a database connection from the postgresql charm, or from
manual specification via charm config.

* `rack` - This will configure the MAAS mode to `rack`. `rack` mode nodes will wait for a relation to a region controller (node with `maas-mode` configured to `region`).

* `region+rack` - This will configure the node to be a region and rack controller (requires external postgresql).


### Basic (maas-mode='all')
Deploying this charm with the defaults will get you MAAS installed in 'all' mode.

For example:

```bash
juju deploy maas
```

The above command will deploy MAAS in 'all' mode.

### Desparate Node Types
The extended functionality of this charm lends itself to the configuration of MAAS deploys with non-uniform `maas-mode`s.

For example:
```yaml
# maas-config.yaml
maas-region:
  maas-mode: "region"
maas-rack:
  maas-mode: "rack"
```

```bash
# Deploy postgresql
juju deploy postgresql

# Deploy 3 units of each type of node
juju deploy maas maas-region -n 3 --config maas-config.yaml

juju deploy maas maas-rack -n 3 --config maas-config.yaml

# Deploy haproxy
juju deploy haproxy

# Relation between region and postgresql
juju relate maas-region:postgresql postgresql:db

# Relation between region and rack
juju relate maas-region:region maas-rack:rack

# Relation between region and haproxy
juju relate maas-region:http haproxy:reverseproxy

```

#### Reconfigure the region and rack controllers to have the maas-url of the haproxy
```bash
juju config maas-region maas-url=http://<haproxy-ip>/MAAS
juju config maas-rack maas-url=http://<haproxy-ip>/MAAS
```

You should now be able to visit `http://<haproxy-ip>/MAAS` in your browser and see your maas nodes all checked in!




# Copyright
* AGPLv3 (see `copyright` file in this directory)

# Contact Information

* James Beedy <jamesbeedy@gmail.com>

