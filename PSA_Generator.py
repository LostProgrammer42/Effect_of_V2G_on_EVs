import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

hours = pd.date_range("2022-01-01 00:00", "2022-01-01 23:00", freq="H")

n = pypsa.Network()
n.set_snapshots(hours)


n.add("Bus", "main_bus")
duck_curve = np.array([
    900, 880, 860, 850, 870, 920, 1000, 1100,   # morning rise
    1050, 950, 800, 700, 650, 680, 750, 900,    # midday dip
    1100, 1300, 1500, 1650, 1750, 1700, 1500, 1200  # evening ramp + peak
])


n.add("Load", "demand", bus="main_bus", p_set=duck_curve)

# Thermal generator (main supply)
n.add(
    "Generator",
    "Thermal_Gen",
    bus="main_bus",
    p_nom=1000,          # installed capacity
    marginal_cost=50,    # cheap to run
    p_min_pu=0.2,        # must run at ≥20% capacity (400 MW)
    efficiency=0.4
)

# Slack generator (expensive backup)
n.add(
    "Generator",
    "Slack_Gen",
    bus="main_bus",
    p_nom=1000,
    marginal_cost=1000,  # very expensive
    p_min_pu=0.0
)

n.optimize(solver_name="highs") 

fig, ax = plt.subplots(figsize=(12, 6))

# Data
thermal = n.generators_t.p["Thermal_Gen"]
slack = n.generators_t.p["Slack_Gen"]

# Plot demand
ax.plot(hours, duck_curve, label="Load (MW)", color="black", linewidth=2, zorder=3)

# Stacked area plot (continuous curves)
ax.fill_between(hours, 0, thermal, label="Thermal Gen", alpha=0.6, color="tab:blue")
ax.fill_between(hours, thermal, thermal + slack, label="Slack Gen", alpha=0.6, color="tab:red")

# Formatting
ax.set_title("Two-Generator System Meeting Duck Curve Load", fontsize=14, fontweight="bold")
ax.set_xlabel("Hour of Day", fontsize=12)
ax.set_ylabel("Power (MW)", fontsize=12)

# Better x-axis (hours only)
ax.set_xticks(hours[::2])
ax.set_xticklabels([h.strftime("%H:%M") for h in hours[::2]], rotation=45)

ax.legend(loc="upper left", frameon=True)
ax.grid(True, linestyle="--", alpha=0.5)

# Duck curve feature annotations
ax.annotate("Morning Rise", xy=(6, duck_curve[6]), xytext=(4, 1300),
            arrowprops=dict(arrowstyle="->", color="gray"))
ax.annotate("Midday Dip", xy=(13, duck_curve[13]), xytext=(11, 500),
            arrowprops=dict(arrowstyle="->", color="gray"))
ax.annotate("Evening Ramp", xy=(19, duck_curve[19]), xytext=(16, 1800),
            arrowprops=dict(arrowstyle="->", color="gray"))

plt.tight_layout()
plt.show()
