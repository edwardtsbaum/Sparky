from dotenv import load_dotenv
import os

load_dotenv()

import motor.motor_asyncio
from urllib.parse import quote_plus

# Escape the username and password
username = os.getenv("MONGO_USERNAME")
password = os.getenv("MONGO_PASSWORD")
mongoHost = os.getenv("MONGO_HOST")
escaped_username = quote_plus(username)
escaped_password = quote_plus(password)

# # Use the escaped username and password in the URI
uri = f"mongodb+srv://{escaped_username}:{escaped_password}@{mongoHost}/"

#'27017' is the default port for mongodb
#client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
client = motor.motor_asyncio.AsyncIOMotorClient(uri)
database = client.Ed

#collection is a table in sql
conversation_state = database.conversation_memory
knowledge = database.knowledge
daily_summaries = database.daily_summaries
weekly_summaries = database.weekly_summaries
monthly_summaries = database.monthly_summaries
