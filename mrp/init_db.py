import psycopg2


conn = psycopg2.connect(database="mrp",host="localhost",user="postgres",password="asdf56y",port="5432")
cur = conn.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS nodes (id serial PRIMARY KEY, nodename varchar(255), nodedescription 
varchar(255));''')
conn.commit()
cur.close()
conn.close()