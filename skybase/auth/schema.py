import os
import sqlite3

from skybase import config as sky_cfg

# these values *must* match those used for checking group.command.planet permissions
ROLES = ['developer', 'operator', 'admin']
ROLES_DEFAULT = 'developer'

# TODO: move schema creation statements to external file (where?)
def create_db(conn):
    schema = '''
        PRAGMA foreign_keys=OFF;
        BEGIN TRANSACTION;

        CREATE TABLE credentials(
          id INTEGER PRIMARY KEY ASC,
          user_id varchar(250) NOT NULL,
          key varchar(250) NOT NULL,
          email varchar(250));

        CREATE INDEX credentials_user_id_idx on credentials (user_id);
        CREATE INDEX credentials_email_idx on credentials (email);

        CREATE TABLE roles(
          id INTEGER PRIMARY KEY ASC,
          role_name varchar(250) NOT NULL
        );

        CREATE INDEX roles_role_name_idx on roles (role_name);

        CREATE TABLE userroles(
          id INTEGER PRIMARY KEY ASC,
          user_id INTEGER,
          role_id INTEGER,
          FOREIGN KEY(user_id) REFERENCES credentials(id),
          FOREIGN KEY(role_id) REFERENCES roles(id)
        );

        CREATE INDEX userroles_user_id_idx on userroles (user_id);
        CREATE INDEX userroles_role_id_idx on userroles (role_id);

        INSERT INTO "roles" VALUES(1,'developer');
        INSERT INTO "roles" VALUES(2,'operator');
        INSERT INTO "roles" VALUES(3,'admin');

        PRAGMA foreign_keys=ON;
        COMMIT;
    '''

    with conn:
        c = conn.cursor()
        c.executescript(schema)

def connect():
    # load database name from config
    runner_cfg = sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR)

    db_file = os.path.join(runner_cfg.data['dbauth']['dir'],
                           runner_cfg.data['dbauth']['filename'])

    # determine if required db exists
    should_create = False
    if not os.path.isfile(db_file):
        should_create = True

    # establish connection and create if doesn't exist
    conn = sqlite3.connect(db_file)
    if should_create:
        create_db(conn)
    return conn


