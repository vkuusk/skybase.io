from skybase.auth import schema
from skybase.exceptions import SkyBaseRoleNotFoundError, SkyBaseUserIdNotFoundError, SkyBaseError


def get_db_conn():
    return schema.connect()


def create_user(user_id, key, email, role):
    db_conn = get_db_conn()

    cursor = db_conn.execute(
        "select count(id) from credentials where user_id = ?", (user_id,))

    count = cursor.fetchone()[0]
    if count > 0:
        if not email or email == '':
            db_conn.execute("update credentials set key = ? where user_id = ?",
                            (key, user_id))
        else:
            db_conn.execute("update credentials set key = ?, email = ? where user_id = ?",
                            (key, user_id, email))
    else:
        db_conn.execute(
            "insert or replace into credentials (user_id,key, email) values (?,?,?)",
            (user_id, key, email))
    db_conn.commit()
    upsert_userroles(user_id, role)


def lookup_key(user_id):
    db_conn = get_db_conn()

    cursor = db_conn.execute("select key from credentials where user_id = ?",
                             (user_id,))
    result = cursor.fetchone()
    if result is None:
        raise SkyBaseUserIdNotFoundError(user_id)

    return result[0]

def find_user_roles(user_id):
    db_conn = get_db_conn()

    with db_conn:
        c = db_conn.cursor()

        query = '''
            select roles.role_name from credentials, userroles, roles
            where userroles.user_id = credentials.id
            and userroles.role_id = roles.id
            and credentials.user_id = ?'''

        c.execute(query, (user_id,))
        roles = c.fetchall()

        return [role[0] for role in roles]

def delete_user(user_id):
    db_conn = get_db_conn()
    db_conn.execute("delete from userroles where user_id = (select id from credentials where user_id = ?)", (user_id,))
    db_conn.execute("delete from credentials where user_id = ?", (user_id,))
    db_conn.commit()


def unique_user_exists(user_id):
    ''' return boolean value testing user existence'''
    db_conn = get_db_conn()
    # query auth db for count of user id
    cursor = db_conn.execute('select count(*) from credentials where user_id = ?', (user_id,))

    # unpack returned value
    (number_of_rows,) = cursor.fetchone()

    # require row count value of one and only one for True
    return (number_of_rows == 1)



def find_user(user_id):
    db_conn = get_db_conn()

    cursor = db_conn.execute('select c.user_id, c.key, c.email, r.role_name from credentials c, roles r, userroles u where c.id = u.user_id and u.role_id = r.id and c.user_id = ?',
                             (user_id,))
    result = cursor.fetchall()
    return result


def upsert_userroles(user_id, role):
    # acquire database connection
    db_conn = get_db_conn()
    with db_conn:
        c = db_conn.cursor()

        # find role id from role name
        c.execute('select id from roles where role_name = ?', (role,))
        roleid = c.fetchone()

        if roleid:
            # find user record id from user name
            c.execute('select id from credentials where user_id = ?', (user_id,))
            userid = c.fetchone()
            if userid:
                # attempt update or insert user role
                update_result = c.execute('update userroles set role_id = ? where user_id = ?', (roleid[0], userid[0]))
                if update_result.rowcount == 0:
                    c.execute("insert into userroles (user_id, role_id) values (?,?)", (userid[0], roleid[0]))
                db_conn.commit()
            else:
                raise SkyBaseUserIdNotFoundError(user_id + 'not found')
        else:
            raise SkyBaseRoleNotFoundError(role + 'not defined')


def update_email(user_id, user_email):
    db_conn = get_db_conn()

    with db_conn:
        c = db_conn.cursor()
        c.execute('select * from credentials where user_id = ?', (user_id,))
        users = c.fetchone()
        if not users:
            raise SkyBaseUserIdNotFoundError(user_id + 'not found')
        else:
            c.execute("update credentials set email = ? where user_id = ?",
                            (user_email, user_id))
            db_conn.commit()


def reset_password(user_id, user_password):
    db_conn = get_db_conn()

    with db_conn:
        c = db_conn.cursor()
        c.execute('select * from credentials where user_id = ?', (user_id,))
        users = c.fetchone()
        if not users:
            raise SkyBaseUserIdNotFoundError(user_id + 'not found')
        else:
            c.execute("update credentials set key = ? where user_id = ?",
                            (user_password, user_id))
            db_conn.commit()


def list_users(user_id='%'):
    db_conn = get_db_conn()
    with db_conn:
        c = db_conn.cursor()
        c.execute("select c.user_id, c.key, c.email, r.role_name from credentials c, roles r, userroles u where c.id = u.user_id and u.role_id = r.id and c.user_id like ?",
                  (user_id,))
        records= c.fetchall()
        return records
