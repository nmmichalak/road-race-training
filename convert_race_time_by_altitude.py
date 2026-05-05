import numpy as np

# ----------------------------
# Wehrlin & Hallén / Sport-Calculator Logic
# ----------------------------

def get_event_exponent(distance_m):
    """
    Returns the alpha exponent based on distance.
    Short (1500-3k): 0.5 | 5k-10k: 0.4 | Half+: 0.3
    """
    if distance_m <= 3000:
        return 0.5
    elif distance_m <= 12000:
        return 0.4
    else:
        return 0.3

def get_acclimation_factor(status_idx, is_native):
    """
    0: Not acclimated, 1: Partial, 2: Full
    """
    factors = [1.0, 0.7, 0.5]
    f_accl = factors[status_idx]
    if is_native:
        f_accl *= 0.7
    return f_accl

def calculate_altitude_adjustment(time_sec, dist_m, target_alt_m, ref_alt_m, accl_idx, is_native, mode='effort'):
    """
    mode 'effort': Sea Level -> Altitude (How much slower will I be?)
    mode 'pace':   Altitude -> Sea Level (What is my true fitness?)
    """
    # 1. Delta Height in km
    delta_h = (target_alt_m - ref_alt_m) / 1000.0
    
    # 2. VO2max Change
    k_vo2_base = 0.07 # 7% per 1000m
    f_accl = get_acclimation_factor(accl_idx, is_native)
    k_vo2_eff = k_vo2_base * f_accl
    
    # r_VO2 represents the remaining percentage of VO2 capacity
    r_vo2 = 1 - (k_vo2_eff * delta_h)
    
    # 3. Speed Conversion (alpha)
    alpha = get_event_exponent(dist_m)
    r_speed = r_vo2**alpha
    
    if mode == 'effort':
        # SL Time / r_speed = Altitude Time
        return time_sec / r_speed
    else:
        # Alt Time * r_speed = SL Time
        return time_sec * r_speed

# ----------------------------
# Formatting & Interface
# ----------------------------

def parse_time(time_str):
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 2: return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]

def format_hms(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    if h > 0: return f"{h:02}:{m:02}:{s:02}"
    return f"{m:02}:{s:02}"

if __name__ == "__main__":
    print("\n" + "="*45)
    print(" ADVANCED ALTITUDE PERFORMANCE CONVERTER ")
    print(" (Wehrlin & Hallén / Sport-Calculator Model) ")
    print("="*45)

    try:
        # Distance Input
        dist_m = float(input("Enter Distance (meters, e.g. 5000): "))
        time_str = input("Enter Time (MM:SS or HH:MM:SS): ")
        total_sec = parse_time(time_str)

        # Altitude Inputs
        target_alt = float(input("Target Altitude (meters, e.g. 1646 for Lafayette): "))
        ref_alt = float(input("Reference Altitude (meters, usually 0): "))

        # Status Inputs
        print("\nAcclimation Status:\n 0: Not (<5 days)\n 1: Partial (5-21 days)\n 2: Full (>3 weeks)")
        accl_idx = int(input("Select status (0-2): "))
        is_native = input("Are you an altitude native? (y/n): ").lower() == 'y'
        
        mode_choice = input("\n[1] Sea Level -> Altitude (Effort Mode)\n[2] Altitude -> Sea Level (Pace Mode)\nChoice: ")
        mode = 'effort' if mode_choice == '1' else 'pace'

        adj_sec = calculate_altitude_adjustment(total_sec, dist_m, target_alt, ref_alt, accl_idx, is_native, mode)

        print("\n" + "-"*45)
        if mode == 'effort':
            print(f"Sea Level Time: {format_hms(total_sec)}")
            print(f"Altitude Time:  {format_hms(adj_sec)}")
            print(f"Difference:    +{format_hms(adj_sec - total_sec)}")
        else:
            print(f"Altitude Time:  {format_hms(total_sec)}")
            print(f"Sea Level Equiv: {format_hms(adj_sec)}")
            print(f"Difference:    -{format_hms(total_sec - adj_sec)}")
        print("-"*45)

    except Exception as e:
        print(f"\n[!] Input Error: {e}")