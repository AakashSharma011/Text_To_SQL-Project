from dotenv import load_dotenv
import os
load_dotenv()

db_url = os.getenv("DATABASE_URL")
print(f"Database URL: {db_url}")