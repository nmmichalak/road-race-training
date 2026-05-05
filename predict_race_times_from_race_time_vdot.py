import numpy as np
import pandas as pd

# ----------------------------
# Corrected Daniels Equations
# ----------------------------

def vo2_running(speed_m_min):
    """
    Oxygen cost of running.
    Note the -4.60 intercept; this is specific to the Daniels/Gilbert curve.
    """
    return -4.60 + 0.182258 * speed_m_min + 0.000104 * speed_m_min**2

def vo2max_fraction(time_min):
    """Fraction of VO2max sustainable for a race of duration t."""
    return (
        0.8
        + 0.1894393 * np.exp(-0.012778 * time_min)
        + 0.2989558 * np.exp(-0.1932605 * time_min)
    )

def vdot_from_race(time_sec, distance_m):
    """Estimate VDOT from a performance."""
    t = time_sec / 60
    v = distance_m / t
    vo2 = vo2_running(v)
    vo2max_frac = vo2max_fraction(t)
    vdot = vo2 / vo2max_frac

    print(f"Estimated V02: {vo2:.1f}")
    print(f"Estimated VDOT: {vdot:.1f}")

    return vdot

def race_time_from_vdot(vdot, distance_m):
    """Inverse solve for race time given a VDOT."""
    def f(t):
        return vo2_running(distance_m / t) / vo2max_fraction(t) - vdot

    # Binary search for time in minutes
    low, high = 2.0, 420.0 
    for _ in range(50):
        mid = (low + high) / 2
        # If cost is higher than VDOT, we are going too fast (need more time)
        if f(mid) > 0: low = mid
        else: high = mid
    return mid * 60

# ----------------------------
# Formatting
# ----------------------------

def format_hms(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02}:{m:02}:{s:02}.00"

def generate_table(ref_dist, ref_time_str):
    # Parse input time (MM:SS or HH:MM:SS)
    parts = list(map(int, ref_time_str.split(':')))
    if len(parts) == 2:
        total_sec = parts[0] * 60 + parts[1]
    else:
        total_sec = parts[0] * 3600 + parts[1] * 60 + parts[2]

    vdot = vdot_from_race(total_sec, ref_dist)
    mile_meters = 1609.344
    
    races = [
        ("1500m", 1500), ("mile", mile_meters), ("3000m", 3000), ("2 mile", 2 * mile_meters),
        ("5k", 5000), ("8k", 8000), ("5 mile", 5 * mile_meters), ("10k", 10000),
        ("15k", 15000), ("10 mile", 10 * mile_meters), ("20k", 20000), ("half marathon", 42195 / 2),
        ("25k", 25000), ("30k", 30000), ("marathon", 42195)
    ]

    print(f"{'race':<20} {'time':<15}")
    print("-" * 35)
    for name, dist in races:
        pred = race_time_from_vdot(vdot, dist)
        print(f"{name:<20} {format_hms(pred)}")

if __name__ == "__main__":
    print("\n--- VDOT Performance Lab ---")
    
    # Distance lookup for convenience
    distance_presets = {
        "1500": 1500,
        "mile": 1609.344,
        "3k": 3000,
        "2m": 3218.688,
        "5k": 5000,
        "8k": 8000,
        "10k": 10000,
        "10m": 16093.44,
        "half": 21097.5,
        "marathon": 42195
    }

    # 1. Get Distance
    print(f"Presets: {', '.join(distance_presets.keys())}")
    dist_input = input("Enter race distance (preset or meters): ").strip().lower()
    
    dist_m = distance_presets.get(dist_input)
    if dist_m is None:
        try:
            dist_m = float(dist_input)
        except ValueError:
            print("Unknown distance. Defaulting to 5000m.")
            dist_m = 5000

    # 2. Get Time
    time_str = input("Enter race time (e.g., 17:03 or 1:18:09): ").strip()

    try:
        # Calculate VDOT and VO2 for display before the table
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 2:
            total_sec = parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            total_sec = parts[0] * 3600 + parts[1] * 60 + parts[2]
        else:
            raise ValueError("Time format must be MM:SS or HH:MM:SS")

        vdot = vdot_from_race(total_sec, dist_m)
        actual_vo2 = vo2_running(dist_m / (total_sec / 60))

        print(f"\n--- Analysis ---")
        print(f"Estimated VO2 Cost: {actual_vo2:.1f}")
        print(f"Estimated VDOT:     {vdot:.1f}")
        print("-" * 35)

        # 3. Generate the table using the function we built earlier
        generate_table(dist_m, time_str)
        
    except Exception as e:
        print(f"\n[!] Error: {e}")
        print("Please ensure your time is in MM:SS or HH:MM:SS format.")