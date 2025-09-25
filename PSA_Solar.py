import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

hours = pd.date_range("2022-01-01 00:00", "2022-01-01 23:00", freq="H")

n = pypsa.Network()
n.set_snapshots(hours)

n.add("Bus", "main_bus")
EV_Total_Load = 2000
EV_Load = np.array([0.090,0.083,0.068,0.045,
0.026,0.012,0.002,0.000,
0.002,0.008,0.011,0.015,
0.015,0.023,0.038,0.033,
0.038,0.038,0.035,0.048,
0.045,0.090,0.120,0.120,
]) * EV_Total_Load

duck_curve = np.array([
    900, 880, 860, 850, 870, 920, 1000, 1100,   # morning rise
    1050, 950, 800, 700, 650, 680, 750, 900,    # midday dip
    1100, 1300, 1500, 1650, 1750, 1700, 1500, 1200  # evening ramp + peak
])
noise = np.random.normal(0, 50, len(duck_curve))
duck_curve = np.clip(duck_curve + noise, 0, None)
load_final = duck_curve + EV_Load
n.add("Load", "demand", bus="main_bus", p_set=load_final)

# --- Generators ---

# Thermal generator (baseline)
n.add(
    "Generator",
    "Thermal_Gen",
    bus="main_bus",
    p_nom=1000,
    marginal_cost=50,
    p_min_pu=0.2,
    efficiency=0.4
)

# Slack generator (expensive backup)
n.add(
    "Generator",
    "Slack_Gen",
    bus="main_bus",
    p_nom=1000,
    marginal_cost=1000,
    p_min_pu=0.0
)

# Solar profile (normalized 0–1)
solar_profile = np.array([
    0,0,0,0,0,0, 0.2,0.6,0.9,1.0,1.0,0.95,
    0.9,0.8,0.6,0.3,0.1,0,0,0,0,0,0,0
])

# Solar generator (large enough to exceed load at midday)
n.add(
    "Generator",
    "Solar",
    bus="main_bus",
    p_nom=2000,              # 2000 MW peak
    p_max_pu=solar_profile,  # availability
    marginal_cost=0.0
)

# --- Solve ---
n.optimize(solver_name="highs")

# Extract results
thermal = n.generators_t.p["Thermal_Gen"]
slack   = n.generators_t.p["Slack_Gen"]
solar   = n.generators_t.p["Solar"]

# Theoretical max solar (capacity × profile)
solar_potential = 2000 * solar_profile

# Curtailment = available - used
solar_curtail = solar_potential - solar

# --- Plot ---
fig, ax = plt.subplots(figsize=(12, 6))

# Demand
ax.plot(hours, duck_curve, label="Domestic Load (MW)", color="blue",alpha = 0.1, linewidth=2, zorder=3)
ax.plot(hours, EV_Load, label="EV Load (MW)", color="green",alpha = 0.1, linewidth=2, zorder=3)
ax.plot(hours, load_final, label="Total Load (MW)", color="black", linewidth=2, zorder=3)


# Stack: Solar used, Thermal, Slack
ax.fill_between(hours, 0, solar, label="Solar Used", alpha=0.6, color="gold")
ax.fill_between(hours, solar, solar + thermal, label="Thermal Gen", alpha=0.6, color="tab:blue")
ax.fill_between(hours, solar + thermal, solar + thermal + slack, label="Slack Gen", alpha=0.6, color="tab:red")

# Curtailment (between used solar and potential)
ax.fill_between(hours, solar, solar_potential,
                color="orange", alpha=0.3, hatch="///",
                label="Solar Curtailment (Wasted)")

# Solar potential line
ax.plot(hours, solar_potential, linestyle="--", color="orange", alpha=0.7,
        label="Solar Potential")

# Formatting
ax.set_title("Load vs Generation", fontsize=14, fontweight="bold")
ax.set_xlabel("Hour of Day", fontsize=12)
ax.set_ylabel("Power (MW)", fontsize=12)
ax.set_xticks(hours[::2])
ax.set_xticklabels([h.strftime("%H:%M") for h in hours[::2]], rotation=45)

ax.legend(loc="upper left", frameon=True)
ax.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
plt.show()
