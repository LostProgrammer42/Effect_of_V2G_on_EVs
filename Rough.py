import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Define the time range for the simulation
hours = pd.date_range("2022-01-01 00:00", "2022-01-01 23:00", freq="H")

# Create a PyPSA network object
n = pypsa.Network()
n.set_snapshots(hours)

# Add a single bus to the network
n.add("Bus", "main_bus")

# Define and add the "duck curve" load profile
duck_curve = np.array([
    900, 880, 860, 850, 870, 920, 1000, 1100,      # morning rise
    1050, 950, 800, 700, 650, 680, 750, 900,       # midday dip
    1100, 1300, 1500, 1650, 1750, 1700, 1500, 1200  # evening ramp + peak
])
n.add("Load", "demand", bus="main_bus", p_set=duck_curve)

# --- Generators ---

# Thermal generator (acts as baseline, has a non-zero minimum output)
n.add(
    "Generator",
    "Thermal_Gen",
    bus="main_bus",
    p_nom=1000,
    marginal_cost=50,
    p_min_pu=0.2,
    efficiency=0.4
)

# Slack generator (acts as an expensive backup to meet any remaining demand)
n.add(
    "Generator",
    "Slack_Gen",
    bus="main_bus",
    p_nom=1000,
    marginal_cost=1000,
    p_min_pu=0.0
)

# Solar profile (normalized from 0 to 1)
solar_profile = np.array([
    0,0,0,0,0,0, 0.2,0.6,0.9,1.0,1.0,0.95,
    0.9,0.8,0.6,0.3,0.1,0,0,0,0,0,0,0
])

# Solar generator (large capacity, no marginal cost)
n.add(
    "Generator",
    "Solar",
    bus="main_bus",
    p_nom=2000,                 # 2000 MW peak capacity
    p_max_pu=solar_profile,     # availability determined by the profile
    marginal_cost=0.0
)

# --- Solve the optimization problem ---
n.optimize(solver_name="highs")

# Extract the generation results from the solved network
thermal = n.generators_t.p["Thermal_Gen"]
slack   = n.generators_t.p["Slack_Gen"]
solar   = n.generators_t.p["Solar"]

# Calculate the theoretical maximum solar output
solar_potential = 2000 * solar_profile

# --- Plot the results with corrected curtailment visualization ---
fig, ax = plt.subplots(figsize=(12, 6))

# Plot the load as the main curve
ax.plot(hours, duck_curve, label="Load (MW)", color="black", linewidth=2, zorder=3)

# Create a stacked area plot for the generators that meet the load
ax.fill_between(hours, 0, solar, label="Solar Used", alpha=0.6, color="gold")
ax.fill_between(hours, solar, solar + thermal, label="Thermal Gen", alpha=0.6, color="tab:blue")
ax.fill_between(hours, solar + thermal, solar + thermal + slack, label="Slack Gen", alpha=0.6, color="tab:red")

# Plot the theoretical solar potential
ax.plot(hours, solar_potential, linestyle="--", color="orange", alpha=0.7,
        label="Solar Potential")

# Correctly plot the curtailment as the area between solar potential and load
# The `where` clause ensures we only plot this area when potential > load
ax.fill_between(
    hours,
    duck_curve,
    solar_potential,
    where=solar_potential > duck_curve,
    color="orange",
    alpha=0.3,
    hatch="///",
    label="Solar Curtailment (Wasted)"
)

# --- Formatting the plot ---
ax.set_title("System with Solar - Corrected Curtailment Plot", fontsize=14, fontweight="bold")
ax.set_xlabel("Hour of Day", fontsize=12)
ax.set_ylabel("Power (MW)", fontsize=12)
ax.set_xticks(hours[::2])
ax.set_xticklabels([h.strftime("%H:%M") for h in hours[::2]], rotation=45)
ax.legend(loc="upper left", frameon=True)
ax.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
plt.show()
