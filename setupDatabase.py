import sqlite3
conn = sqlite3.connect('UserInfo.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS link_data (
        user_id INTEGER PRIMARY KEY,
        access_token TEXT,
        refresh_token TEXT,
        xbl3token TEXT
    )
''')

print("""
--==--==--==--==--==--==--==--==--==--==-
Table 1 created!
--==--==--==--==--==--==--==--==--==--==-
""".strip())

c.execute('''
    CREATE TABLE IF NOT EXISTS invitetable (
        user_id INTEGER PRIMARY KEY,
        invites INTEGER,
        invitesused INTEGER,
        currentlyinviting TEXT,
        claimeddaily TEXT
    )
''')

print("""
--==--==--==--==--==--==--==--==--==--==-
Table 2 created!
--==--==--==--==--==--==--==--==--==--==-
""".strip())

# Create a table if it doesn't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY,
        name TEXT,
        function_name TEXT,
        data TEXT,
        start_time TEXT
    )
''')

print("""
--==--==--==--==--==--==--==--==--==--==-
Table 3 created!
--==--==--==--==--==--==--==--==--==--==-
""".strip())


print("""
Tables Finished!
--==--==--==--==--==--==--==--==--==--==-
""".strip())

conn.commit()
conn.close()