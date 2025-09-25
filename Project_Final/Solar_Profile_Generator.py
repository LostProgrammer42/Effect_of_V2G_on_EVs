import pandas as pd
import numpy as np
import glob
import os
import warnings
warnings.filterwarnings('ignore')
# Path where monthly XLSX files are stored
folder = "./Solar_Data"

# Collect all Excel files
files = sorted(glob.glob(os.path.join(folder, "*.xlsx")))
monthly_profiles = {}

for f in files:
    print(f"Reading: {f}")
    # Read Sheet-2 only
    df = pd.read_excel(f, sheet_name=2)
    print(df.columns)
    df = df[["Time", "Solar+Wind"]].copy()

    # Parse timestamps
    df["Time"] = pd.to_datetime(df["Time"])
    df = df.sort_values("Time")

    # Resample to hourly
    hourly = df.set_index("Time").resample("H").mean().reset_index()

    # Extract month name (e.g., "2023-09")
    month_label = hourly["Time"].dt.to_period("M").iloc[0].strftime("%Y-%m")

    # Compute average profile (group by hour of day)
    avg_profile = hourly.groupby(hourly["Time"].dt.hour)["Solar+Wind"].mean().values

    # Save raw MW and normalized profile
    P_solar = avg_profile
    if P_solar.max() > 0:
        solar_profile = P_solar / P_solar.max()
    else:
        solar_profile = np.zeros_like(P_solar)

    monthly_profiles[month_label] = {
        "P_solar": P_solar,
        "solar_profile": solar_profile
    }

# Save outputs
np.save("monthly_profiles.npy", monthly_profiles)

avg_P_max = 0
avg_Solar_profile = np.zeros(24)
for m, prof in monthly_profiles.items():
    avg_P_max += prof['P_solar'].max()/12
    avg_Solar_profile += prof['solar_profile']/12

print(f"P_Max: {avg_P_max} MW")
print(f"Profile: {avg_Solar_profile}")
