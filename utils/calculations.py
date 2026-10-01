import math

def calculate_piece_m2(p_length_cm, p_width_cm):
    return (p_length_cm / 100) * (p_width_cm / 100)

def calculate_fire_and_gross(target_m2, target_pcs, sales_unit, piece_m2, edge_trim, breakage_rate, saw_kerf_mm):
    total_fire_pct = edge_trim + breakage_rate + ((saw_kerf_mm / 10) * 2)
    req_gross_m2 = target_m2 * (1 + (total_fire_pct / 100))
    req_gross_pcs = math.ceil(target_pcs * (1 + (total_fire_pct / 100)))
    return total_fire_pct, req_gross_m2, req_gross_pcs

def calculate_crate_capacity(pcs_per_box, boxes_in_crate, piece_m2, p_thickness_cm, density, crate_tare_kg):
    crate_pcs_cap = pcs_per_box * boxes_in_crate
    crate_m2_cap = crate_pcs_cap * piece_m2
    stone_weight = (crate_pcs_cap * piece_m2) * (p_thickness_cm / 100) * (density * 1000)
    crate_gross_weight = stone_weight + crate_tare_kg
    return crate_pcs_cap, crate_m2_cap, crate_gross_weight
