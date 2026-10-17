import os  
from pathlib import Path


import dotenv
from dotenv import load_dotenv as d

import psycopg

d(Path(__file__).with_name(".env"))

print("Connecting to PostgreSQL...", flush=True)
with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5) as connection:
    
   with connection.cursor() as cursor:
       
       
       cursor.execute("""explain(analyze  , FORMAT JSON)
                      select * 
                      from orders 
                      where total = %s
                      
                      """, (40,))
       result = cursor.fetchone()
       report = result[0][0]
       plan = report["Plan"]

       print("Scan method:", plan["Node Type"])
       print("Matching rows:", plan["Actual Rows"])
       print("Execution time:", report["Execution Time"], "ms")
       print("Plan rows:", plan["Plan Rows"])
       
       
       
