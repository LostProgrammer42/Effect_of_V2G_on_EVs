import numpy as np
import matplotlib.pyplot as plt

# -------------------------------
# Generator Class
# -------------------------------
class Generator:
    def __init__(self, name, p_max, inertia, damping, droop=0.05, response_rate=0.2):
        """
        p_max        : Max generator power (MW)
        inertia      : Inertia constant (seconds)
        damping      : Damping factor (MW/Hz)
        droop        : Droop (pu frequency change per pu power)
        response_rate: Rate of response (0-1)
        """
        self.name = name
        self.p_max = p_max
        self.inertia = inertia
        self.damping = damping
        self.droop = droop
        self.response_rate = response_rate
        self.current_output = 0.0
        self.p_output = []

    def dispatch(self, freq_dev, demand_share):
        """
        Adjust generator output using droop control with inertia (gradual response)
        """
        # Droop response setpoint
        setpoint = np.clip(demand_share - freq_dev / self.droop, 0, self.p_max)

        # Smooth inertia-based adjustment
        self.current_output += self.response_rate * (setpoint - self.current_output)
        self.p_output.append(self.current_output)
        return self.current_output

# -------------------------------
# Load Profile Class
# -------------------------------
class LoadProfile:
    def __init__(self, base_load, peak_load, hours=24, dt=0.1, noise_std=1.0):
        self.base_load = base_load
        self.peak_load = peak_load
        self.hours = hours
        self.dt = dt
        self.noise_std = noise_std
        self.time = np.arange(0, hours, dt)
        self.profile = self._generate_duck_curve()

    def _generate_duck_curve(self):
        base_curve = (self.base_load +
                      (self.peak_load - self.base_load) *
                      np.exp(-0.5 * ((self.time - 19) / 3) ** 2) +
                      0.2 * self.base_load * np.sin(0.5 * self.time))
        noise = np.random.normal(0, self.noise_std, len(self.time))
        return base_curve + noise

# -------------------------------
# Grid Class
# -------------------------------
class Grid:
    def __init__(self, generators, load_profile, nominal_freq=50, dt=0.1, damping=1.0):
        self.generators = generators
        self.load_profile = load_profile
        self.nominal_freq = nominal_freq
        self.dt = dt
        self.damping = damping
        self.frequency = [nominal_freq]

    def run_simulation(self):
        total_capacity = sum(g.p_max for g in self.generators)

        for demand in self.load_profile.profile:
            freq = self.frequency[-1]
            freq_dev = freq - self.nominal_freq

            # Base share of load according to generator capacity
            base_shares = [demand * (g.p_max / total_capacity) for g in self.generators]

            # Dispatch with droop and inertia
            gen_power = sum(
                g.dispatch(freq_dev, base_shares[i]) for i, g in enumerate(self.generators)
            )

            # Swing equation for frequency update
            total_inertia = sum(g.inertia for g in self.generators)
            df_dt = (gen_power - demand - self.damping * freq_dev) / (2 * total_inertia * self.nominal_freq)
            new_freq = freq + df_dt * self.dt
            self.frequency.append(new_freq)

    def plot_results(self):
        time = self.load_profile.time
        gen_outputs = np.array([g.p_output for g in self.generators])

        plt.figure(figsize=(12, 6))

        # Frequency plot
        plt.subplot(2, 1, 1)
        plt.plot(time, self.frequency[:-1], label="Frequency (Hz)", color="blue")
        plt.axhline(self.nominal_freq, color="red", linestyle="--", label="Nominal 50 Hz")
        plt.xlabel("Time (hours)")
        plt.ylabel("Frequency (Hz)")
        plt.legend()
        plt.grid(True)

        # Power dispatch plot
        plt.subplot(2, 1, 2)
        plt.stackplot(time, gen_outputs, labels=[g.name for g in self.generators])
        plt.plot(time, self.load_profile.profile, "k--", label="Load")
        plt.xlabel("Time (hours)")
        plt.ylabel("Power (MW)")
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        plt.show()

# -------------------------------
# Example Usage
# -------------------------------
if __name__ == "__main__":
    np.random.seed(42)  # Reproducibility

    # Define generators with inertia and droop
    gen1 = Generator("Coal", p_max=50, inertia=5.0, damping=1.0, droop=0.05, response_rate=0.2)
    gen2 = Generator("Gas", p_max=30, inertia=3.0, damping=1.0, droop=0.05, response_rate=0.3)
    gen3 = Generator("Hydro", p_max=20, inertia=2.0, damping=0.5, droop=0.05, response_rate=0.4)

    # Define load profile with random fluctuations
    load = LoadProfile(base_load=40, peak_load=80, hours=24, dt=0.1, noise_std=1.5)

    # Create and run grid simulation
    grid = Grid([gen1, gen2, gen3], load, nominal_freq=50, dt=0.1)
    grid.run_simulation()
    grid.plot_results()
