import os  
from pathlib import Path


import dotenv
from dotenv import load_dotenv as d

import psycopg

d(Path(__file__).with_name(".env"))

with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
    
   with connection.cursor() as cursor:
       cursor.execute("""CREATE table Customers
       (id int primary key,
        DOB DATE,
        email varchar(40)
        )""")
       
print("customers created")