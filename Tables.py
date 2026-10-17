import os  
from pathlib import Path


import dotenv
from dotenv import load_dotenv as d

import psycopg

d(Path(__file__).with_name(".env"))

print("Connecting to PostgreSQL...", flush=True)
with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5) as connection:
    
   with connection.cursor() as cursor:
       print("Connected. Creating customers table...", flush=True)
       cursor.execute("SET statement_timeout = '5s'")
       cursor.execute("""CREATE table Customers
       (id int primary key,
        DOB DATE,
        email varchar(40)
        )""")
       
print("customers created")
