import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
# Replace with your Excel file path
file_path = ".\Load_Data\Daily_Demand_Profile_2.xlsx"

# Load the Excel sheet
df = pd.read_excel(file_path, sheet_name=0)

# Ensure column names are clean
df = df.rename(columns={
    "Date": "Date",
    "Hour": "Hour",
    "Hourly Demand Met (in MW)": "Demand_MW"
})

normalized_profiles = []
max_values = []

for date, group in df.groupby("Date"):
    group = group.sort_values("Hour")
    demand = group["Demand_MW"].values

    max_demand = demand.max()
    max_values.append(max_demand)

    if max_demand > 0:
        norm = demand / max_demand
    else:
        norm = np.zeros_like(demand)

    normalized_profiles.append(norm)

# Step 2: Average normalized profiles across dates
avg_normalized_profile = np.mean(normalized_profiles, axis=0)

# Step 3: Overall max demand value
overall_max = max(max_values)

print("Average Normalized Load Profile (24 values):")
print(avg_normalized_profile.tolist())
print("\nMaximum Load Value across all dates (MW):", overall_max)