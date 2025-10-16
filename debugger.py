
# from core.datalake import get_voyage_data
# import pandas as pd

# ship = "icon1"
# df = get_voyage_data(ship)

# print("✅ Columns:", list(df.columns))
# print("✅ Head:")
# print(df.head(10)[["sea", "harbor"]])
# print("⚙️ Unique Harbor values:", df["harbor"].unique()[:10])
# print("⚙️ Unique Sea values:", df["sea"].unique()[:10])

import os
from dotenv import load_dotenv
# Load environment variables from .env file in the config folder
load_dotenv(dotenv_path='config/settings.env')
api_key=os.getenv("AZURE_OPENAI_KEY"),
api_version="2024-08-01-preview",
azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),

print(f"api key is {api_key}, azure endpoint is {azure_endpoint}, api version is {api_version}")