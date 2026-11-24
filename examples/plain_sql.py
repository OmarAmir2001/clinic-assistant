# examples/plain_sql.py
"""Talking to a database the plain way: Python's built-in sqlite3, and SQL written by hand.

    uv run python examples/plain_sql.py

The database lives in memory, so nothing is saved: it's only for trying things.
"""
import sqlite3

connection = sqlite3.connect(":memory:")

# 1. Create a table: SQL, inside a Python string
connection.execute("""
    CREATE TABLE doctors (
        id      INTEGER PRIMARY KEY,
        name    TEXT    NOT NULL,
        fee_egp INTEGER NOT NULL CHECK (fee_egp > 0)
    )
""")

# 2. Add rows. Each ? is filled in separately, never glued into the SQL text
connection.execute("INSERT INTO doctors (id, name, fee_egp) VALUES (?, ?, ?)", (1, "Dr. Mona Adel", 450))
connection.execute("INSERT INTO doctors (id, name, fee_egp) VALUES (?, ?, ?)", (2, "Dr. Karim Hassan", 400))
connection.commit()

# 3. Read them back. Each row is a tuple: you must remember that the fee is row[2]
for row in connection.execute("SELECT id, name, fee_egp FROM doctors"):
    print(row)

# 4. The database keeps its rules: a fee of 0 breaks the CHECK
try:
    connection.execute("INSERT INTO doctors (id, name, fee_egp) VALUES (?, ?, ?)", (3, "Dr. Free", 0))
except sqlite3.IntegrityError as error:
    print("Refused:", error)
