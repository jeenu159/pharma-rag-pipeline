import psycopg

conn = psycopg.connect("host=localhost port=5434 dbname=pharma user=rag password=rag")
cur = conn.cursor()
cur.execute("SELECT version();")
print(cur.fetchone()[0])
conn.close()