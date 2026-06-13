from database_connection.conn import *
print("dotad")
conn = make_connection()
if not conn:
    print("Nie udalo sie polaczyc!")
else:
    print("Polaczono!")

cur = conn.cursor()

query = "INSERT INTO rates.testtab VALUES (3, 'pa')"
try:
    cur.execute(query)
except:
    conn.rollback()
else:
    conn.commit()

cur.close()
conn.close()