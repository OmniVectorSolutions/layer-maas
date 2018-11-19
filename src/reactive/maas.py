from subprocess import call

from charmhelpers.core.hookenv import (
#    network_get,
    config,
    leader_get,
    open_port,
    status_set,
    unit_get,
)

from charms.reactive import (
    clear_flag,
    endpoint_from_flag,
    is_flag_set,
    set_flag,
    when,
    when_any,
    when_not,
)

from charmhelpers.core import unitdata

import charms.leadership


#PRIVATE_IP = network_get('http')['ingress-addresses'][0]
PRIVATE_IP = unit_get('private-address')
MAAS_WEB_PORT = 5240


set_flag('maas.mode.{}'.format(config('maas-mode')))


kv = unitdata.kv()


def maas_url():
    if config('maas-url'):
        return config('maas-url')
    else:
        return 'http://{}:5240/MAAS'.format(PRIVATE_IP)


@when('postgresql.connected')
@when_any('maas.mode.region',
          'maas.mode.region+rack')
@when_not('maas.database.requested')
def request_postgresql_database_for_maas_region(pgsql):
    """Request PGSql DB
    """

    conf = config()
    status_set('maintenance', 'Requesting MAASDB')

    pgsql.set_database(conf.get('db-name', 'maasdb'))
    if conf.get('db-roles'):
        pgsql.set_roles(conf.get('db-roles'))
    if conf.get('db-extensions'):
        pgsql.set_extensions(conf.get('db-extensions'))
    status_set('active', 'MAASDB requested')
    set_flag('maas.database.requested')


@when('postgresql.master.available',
      'maas.database.requested')
@when_any('maas.mode.region',
          'maas.mode.region+rack')
@when_not('maas.juju.database.available')
def get_set_postgresql_data_for_maas_db(pgsql):
    """Get/set postgresql details
    """

    status_set('maintenance', 'Database acquired, saving details')
    kv.set('db_host', pgsql.master.host)
    kv.set('db_name', pgsql.master.dbname)
    kv.set('db_pass', pgsql.master.password)
    kv.set('db_user', pgsql.master.user)
    status_set('active', 'MAASDB saved to unitdata')

    clear_flag('maas.manual.database.available')
    set_flag('maas.juju.database.available')


@when('snap.installed.maas',
      'leadership.is_leader')
@when_any('maas.juju.database.available',
          'maas.manual.database.available')
@when_any('maas.mode.region',
          'maas.mode.region+rack')
@when_not('maas.init.complete')
def maas_leader_init():
    """Init MAAS (region, region+rack) - only leader should run this code
    """
    status_set('maintenance',
               'Configuring MAAS-{}'.format(config('maas-mode')))

    init_ctxt = {'maas_url': maas_url(),
                 'maas_mode': config('maas-mode'),
                 'db_host': kv.get('db_host'),
                 'db_name': kv.get('db_name'),
                 'db_pass': kv.get('db_pass'),
                 'db_user': kv.get('db_user')}

    cmd_init = ('maas init --maas-url {maas_url} --database-host {db_host} '
                '--database-name {db_name} --database-user {db_user} '
                '--database-pass {db_pass} --mode {maas_mode} '
                '--force'.format(**init_ctxt))

    call(cmd_init.split())
    status_set('active', 'MAAS-{} configured'.format(config('maas-mode')))
    set_flag('maas.init.complete')


@when('snap.installed.maas',
      'leadership.is_leader',
      'maas.mode.all')
@when_not('maas.init.complete')
def maas_init_mode_all():
    """Init MAAS all mode
    """
    status_set('maintenance',
               'Configuring MAAS-{}'.format(config('maas-mode')))

    init_ctxt = {'maas_url': maas_url(),
                 'maas_mode': config('maas-mode')}

    cmd_init = ('maas init --maas-url {maas_url} --mode all '
                '--force --skip-admin'.format(**init_ctxt))
    call(cmd_init.split())

    status_set('active', 'MAAS-{} configured'.format(config('maas-mode')))
    set_flag('maas.init.complete')


@when('leadership.is_leader',
      'maas.init.complete')
@when_any('maas.mode.region',
          'maas.mode.region+rack',
          'maas.mode.all')
@when_not('maas.admin.created',
          'leadership.set.init_complete')
def create_maas_admin():
    """Create MAAS admin
    """
    super_user_ctxt = {'admin_password': config('admin-password'),
                       'admin_username': config('admin-username'),
                       'admin_email': config('admin-email')}

    cmd_create_super_user = ('maas createadmin --username {admin_username} '
                             '--password {admin_password} '
                             '--email {admin_email}'.format(**super_user_ctxt))
    call(cmd_create_super_user.split())

    # Now the admin is created, init is complete
    charms.leadership.leader_set(init_complete="true")
    set_flag('maas.admin.created')


@when('leadership.is_leader',
      'maas.init.complete')
@when_any('maas.mode.region',
          'maas.mode.region+rack')
@when_not('leadership.set.secret')
def get_set_secret():
    with open("/var/snap/maas/current/var/lib/maas/secret", 'r') as f:
        charms.leadership.leader_set(secret=f.read())


@when('leadership.set.secret')
@when_not('leadership.is_leader',
          'maas.init.complete')
@when_any('maas.mode.region',
          'maas.mode.region+rack')
@when_any('maas.juju.database.available',
          'maas.manual.database.available')
def init_non_leader_region_or_region_rack():
    status_set('maintenance',
               'Configuring MAAS-{}'.format(config('maas-mode')))

    init_ctxt = {'maas_url': maas_url(),
                 'maas_mode': config('maas-mode'),
                 'db_host': kv.get('db_host'),
                 'db_name': kv.get('db_name'),
                 'db_pass': kv.get('db_pass'),
                 'db_user': kv.get('db_user')}

    cmd_init = ('maas config --maas-url {maas_url} --database-host {db_host} '
                '--database-name {db_name} --database-user {db_user} '
                '--database-pass {db_pass} --mode {maas_mode} '
                '--force'.format(**init_ctxt))

    call(cmd_init.split())

    status_set('active', 'MAAS-{} configured'.format(config('maas-mode')))
    set_flag('maas.init.complete')


@when('maas.init.complete')
@when_any('maas.mode.region',
          'maas.mode.all',
          'maas.mode.region+rack')
@when_not('maas.http.available')
def open_web_port():
    open_port(MAAS_WEB_PORT)
    status_set('active', 'MAAS http available')
    set_flag('maas.http.available')


@when('leadership.set.secret',
      'leadership.is_leader',
      'endpoint.region.available')
@when_any('maas.mode.region',
          'maas.mode.region+rack')
@when_not('region.relation.data.available')
def send_relation_data_to_rack():
    endpoint = endpoint_from_flag('endpoint.region.available')
    ctxt = {'secret': leader_get('secret'),
            'maas_url': maas_url()}
    endpoint.configure(**ctxt)
    set_flag('region.relation.data.available')


@when('maas.mode.rack',
      'endpoint.rack.available')
@when_not('rack.relation.data.available')
def acquire_config_from_region_controller():
    """Acquire maas_url and secret from region
    """
    status_set('maintenance',
               'Acquiring configuration details from region controller')
    endpoint = endpoint_from_flag('endpoint.rack.available')
    for unit in endpoint.list_unit_data():
        kv.set('maas_url', unit['maas_url'])
        kv.set('secret', unit['secret'])
    status_set('active', 'Region configuration acquired')
    set_flag('rack.relation.data.available')


@when('rack.relation.data.available',
      'maas.mode.rack')
@when_not('maas.init.complete')
def configure_maas_rack():
    """Configure rack controller now that we have what we need
    """
    status_set('maintenance', 'Rack initializing')
    init_ctxt = {'maas_url': kv.get('maas_url'),
                 'secret': kv.get('secret')}
    cmd_init = \
        ('maas init --maas-url {maas_url} --secret {secret} '
         '--mode rack --force'.format(**init_ctxt))
    call(cmd_init.split())
    status_set('active', 'Rack init complete')
    set_flag('maas.init.complete')


@when('maas.init.complete',
      'maas.mode.rack')
def set_connected_status():
    status_set('active', "Region <-> Rack connected")


@when('maas.mode.region')
@when_not('maas.manual.database.available',
          'maas.juju.database.available')
def block_until_database_info_set():
    """Block region-controller has set database info
    """
    status_set('blocked',
               'Need database connection info via config or relation')
    return


@when('maas.mode.rack')
@when_not('rack.relation.data.available')
def block_until_region_relation():
    """Block rack controllers until relation to region is acquired
    """
    status_set('blocked',
               'Need relation to region controller to continue')
    return


@when('endpoint.http.joined')
@when_any('maas.mode.region',
          'maas.mode.all',
          'maas.mode.region+rack')
@when_not('http.relation.data.available')
def set_http_relation_data():
    endpoint = endpoint_from_flag('endpoint.http.joined')
    ctxt = {'host': PRIVATE_IP, 'port': MAAS_WEB_PORT}
    endpoint.configure(**ctxt)
    set_flag('http.relation.data.available')


@when('config.changed.maas-url',
      'maas.init.complete')
def react_to_config_changed_maas_url():
    status_set('maintenance',
               'Reconfiguring maas-url')
    call('maas config --maas-url {}'.format(maas_url()).split())
    status_set('active',
               'maas-url reconfigured to {}'.format(maas_url()))
