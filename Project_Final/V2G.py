import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

hours = pd.date_range("2022-01-01 00:00", "2022-01-01 23:00", freq="H")

n = pypsa.Network()
n.set_snapshots(hours)

n.add("Bus", "main_bus")

Normalized_Load = np.array([0.7577501967973916, 0.739805740179444, 0.7236425422806064, 0.7167554231733221, 0.7289250057644614, 0.7714951706178165, 0.8265810310571715, 0.8790824660440677, 0.9155464243592003, 0.9470454925165577, 0.9619121517351206, 0.964467442854757, 0.9567006049840137, 0.935814561556312, 0.9171227622542776, 0.9053691214039998, 0.8965894983220128, 0.9131303418800689, 0.981645190522445, 0.9767607899375252, 0.9203511944365227, 0.8805342280768892, 0.8512557333958513, 0.8259928401372565])
Max_Load = 161386.94
load_final = Normalized_Load*Max_Load
n.add("Load", "demand", bus="main_bus", p_set=load_final)

# --- EV as Storage ---

num_EVs = 5_600_000
battery_capacity_kWh = 40     # per EV
total_capacity_MWh = num_EVs * battery_capacity_kWh / 1000  # in MWh
total_capacity_MW = total_capacity_MWh  # assuming 1h resolution
P_total_Max_EV = 70000
# Add storage unit
n.add("StorageUnit",
      "EV_Fleet",
      bus="main_bus",
      p_nom=P_total_Max_EV,                       # max charging/discharging power (MW)
      capital_cost = 0,
      max_hours=total_capacity_MWh / P_total_Max_EV,  # hours of full power
      efficiency_store=0.95,
      efficiency_dispatch=0.95,
      state_of_charge_initial=0.5 * total_capacity_MWh,  # start at 50% SOC
      state_of_charge_min=0.3 * total_capacity_MWh,      # 30% SOC min
      cyclic_state_of_charge=True,
      marginal_cost=1.0)  # very cheap flexibility

# --- Solve ---
n.optimize(solver_name="highs")


# --- Generators ---

# Thermal generator (baseline)
n.add(
    "Generator",
    "Thermal_Gen",
    bus="main_bus",
    p_nom=200000,
    marginal_cost=50,
    p_min_pu=0.2,
    efficiency=0.4
)

n.add(
    "Generator",
    "Hydropower",
    bus="main_bus",
    p_nom=50000,
    marginal_cost=40,
    p_min_pu=0.4
)


# Slack generator (expensive backup)
n.add(
    "Generator",
    "Slack_Gen",
    bus="main_bus",
    p_nom=100000,
    marginal_cost=1000,
    p_min_pu=0.0
)


solar_profile = np.array([0.21673631, 0.21191633, 0.20672958, 0.20005439, 0.19256323, 0.18435334,
 0.19490409, 0.30168449, 0.52745781, 0.75161649, 0.90866067, 0.98641145,
 0.9997654,  0.97321698, 0.89745004, 0.75760522, 0.56115675, 0.34809376,
 0.23500542, 0.21850131, 0.21957297, 0.22213894, 0.22196219, 0.2206215])
P_Solar_Max = 200105.71993774092 
# Solar generator (large enough to exceed load at midday)
n.add(
    "Generator",
    "Solar",
    bus="main_bus",
    p_nom=P_Solar_Max,              # 2000 MW peak
    p_max_pu=solar_profile,  # availability
    marginal_cost=0.0
)

# --- Solve ---
n.optimize(solver_name="highs")

# Extract results
thermal = n.generators_t.p["Thermal_Gen"]
hydro = n.generators_t.p["Hydropower"]
slack   = n.generators_t.p["Slack_Gen"]
solar   = n.generators_t.p["Solar"]
ev_dispatch = n.storage_units_t.p["EV_Fleet"]
ev_charge = -ev_dispatch.clip(upper=0)   # charging load (MW)
ev_discharge = ev_dispatch.clip(lower=0) # discharging gen (MW)


# Theoretical max solar (capacity × profile)
solar_potential = P_Solar_Max * solar_profile

# Curtailment = available - used
solar_curtail = solar_potential - solar

# --- Plot ---
fig, ax = plt.subplots(figsize=(12, 6))

# Demand
ax.plot(hours, Normalized_Load*Max_Load, label="Domestic Load (MW)", color="blue",alpha = 0.1, linewidth=2, zorder=3)
ax.plot(hours, ev_charge, label="EV Load (MW)", color="green",alpha = 1, linewidth=2, zorder=3)
ax.plot(hours, load_final+ev_charge, label="Total Load (MW)", color="black", linewidth=2, zorder=3)


# Stack: Solar used, Thermal, Slack
ax.fill_between(hours, 0, solar, label="Solar Used", alpha=0.6, color="gold")
ax.fill_between(hours, solar, solar + thermal, label="Thermal Gen", alpha=0.6, color="tab:blue")
ax.fill_between(hours, solar + thermal, solar + thermal + hydro, label="Hydro Gen", alpha=0.6, color="tab:green")
ax.fill_between(hours, solar + thermal + hydro, solar + thermal + hydro + abs(ev_discharge), label="EV V2G", alpha=0.6, color="tab:purple")
ax.fill_between(hours, solar + thermal + hydro + abs(ev_discharge), solar + thermal + hydro + abs(ev_discharge) + slack, label="Slack Gen", alpha=0.6, color="tab:red")

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
plt.savefig("./Project_Final/Normal_Grid_With_V2G.png")
plt.show()

curtailment = np.maximum(solar_potential - solar, 0)
print("Total curtailed solar energy:", sum(curtailment), "MWh")
