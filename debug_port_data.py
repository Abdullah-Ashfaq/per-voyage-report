
from core.datalake import get_voyage_data
import pandas as pd

ship = "icon1"
df = get_voyage_data(ship)

print("✅ Columns:", list(df.columns))
print("✅ Head:")
print(df.head(10)[["sea", "harbor"]])
print("⚙️ Unique Harbor values:", df["harbor"].unique()[:10])
print("⚙️ Unique Sea values:", df["sea"].unique()[:10])
