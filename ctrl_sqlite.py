import sqlite3
from contextlib import closing

dbname = 'name.db'

def main():
    global dbname

    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()

        create_table = 'create table users(id varchar(16) primary key, name varchar(64))'

        c.execute(create_table)

def search(user_id):
    global dbname
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        search_user = 'select name from users where id=?'
        u_id = (user_id,)
        c.execute(search_user, u_id)
        res = c.fetchone()
    #返り値はNoneかタプル res[0]に名前が入ってる
    return res


def insert(user_id, name):
    global dbname
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        insert_sql = 'insert into users values (?, ?)'
        u_id = (user_id, name)
        c.execute(insert_sql, u_id)
        conn.commit()

if __name__ == '__main__':
    main()