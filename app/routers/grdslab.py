from fastapi import APIRouter, Query
from app.grdslab.calculator import calculate_full

router = APIRouter(tags=["GRDSLAB"])

CONVERSIONS = {
    "in_to_mm": 25.4,
    "mm_to_in": 1 / 25.4,
    "psi_to_MPa": 0.00689476,
    "MPa_to_psi": 145.0377,
    "pci_to_kPa_mm": 0.271447,
    "kPa_mm_to_pci": 1 / 0.271447,
    "kip_to_kN": 4.44822,
    "kN_to_kip": 1 / 4.44822,
}

SOIL_TYPES = [
    {"name": "Blended granular base", "k_pci": 300, "k_kPa_mm": 81.4, "description": "Crushed stone, well-graded"},
    {"name": "Cement-treated base", "k_pci": 500, "k_kPa_mm": 135.7, "description": "CTB, high stiffness"},
    {"name": "Lean concrete base", "k_pci": 600, "k_kPa_mm": 162.9, "description": "Economical subbase"},
    {"name": "Lime-stabilized subgrade", "k_pci": 150, "k_kPa_mm": 40.7, "description": "Treatment for expansive clays"},
    {"name": "Sand-gravel (dense)", "k_pci": 200, "k_kPa_mm": 54.3, "description": "Well-compacted granular fill"},
    {"name": "Silty sand", "k_pci": 100, "k_kPa_mm": 27.1, "description": "Common native soil"},
    {"name": "Clay (stiff)", "k_pci": 75, "k_kPa_mm": 20.4, "description": "Moderate bearing capacity"},
    {"name": "Clay (medium)", "k_pci": 50, "k_kPa_mm": 13.6, "description": "Needs stabilization for heavy loads"},
    {"name": "Clay (soft)", "k_pci": 25, "k_kPa_mm": 6.8, "description": "Poor bearing â€” thick slab required"},
    {"name": "Peat / organic", "k_pci": 10, "k_kPa_mm": 2.7, "description": "Very low â€” ground improvement needed"},
]

FORKLIFT_TABLE = [
    {"model": "Toyota 3F4", "capacity_kg": 1000, "load_kN": 9.8, "wheel_load_kN": 2.45, "contact_area_mm2": 18000, "axles": 2},
    {"model": "Toyota 6F4", "capacity_kg": 1500, "load_kN": 14.7, "wheel_load_kN": 3.68, "contact_area_mm2": 22000, "axles": 2},
    {"model": "Toyota 8F4", "capacity_kg": 2000, "load_kN": 19.6, "wheel_load_kN": 4.90, "contact_area_mm2": 26000, "axles": 2},
    {"model": "Toyota 8F5", "capacity_kg": 2500, "load_kN": 24.5, "wheel_load_kN": 6.13, "contact_area_mm2": 30000, "axles": 2},
    {"model": "Toyota 9F5", "capacity_kg": 3000, "load_kN": 29.4, "wheel_load_kN": 7.35, "contact_area_mm2": 34000, "axles": 2},
    {"model": "Toyota 9F6", "capacity_kg": 3500, "load_kN": 34.3, "wheel_load_kN": 8.58, "contact_area_mm2": 38000, "axles": 2},
    {"model": "Hyster H50XL", "capacity_kg": 2268, "load_kN": 22.2, "wheel_load_kN": 5.56, "contact_area_mm2": 28000, "axles": 2},
    {"model": "Hyster H70XL", "capacity_kg": 3175, "load_kN": 31.1, "wheel_load_kN": 7.78, "contact_area_mm2": 36000, "axles": 2},
    {"model": "Hyster H100XL", "capacity_kg": 4536, "load_kN": 44.5, "wheel_load_kN": 11.13, "contact_area_mm2": 44000, "axles": 2},
    {"model": "Crown SP 4200", "capacity_kg": 1814, "load_kN": 17.8, "wheel_load_kN": 4.45, "contact_area_mm2": 24000, "axles": 2},
    {"model": "Raymond 4150", "capacity_kg": 1361, "load_kN": 13.3, "wheel_load_kN": 3.33, "contact_area_mm2": 20000, "axles": 2},
    {"model": "JLG 660SJ (boom)", "capacity_kg": 227, "load_kN": 2.2, "wheel_load_kN": 0.56, "contact_area_mm2": 12000, "axles": 2},
    {"model": "CAT DP15", "capacity_kg": 1361, "load_kN": 13.3, "wheel_load_kN": 3.33, "contact_area_mm2": 20000, "axles": 2},
    {"model": "CAT DP25", "capacity_kg": 2268, "load_kN": 22.2, "wheel_load_kN": 5.56, "contact_area_mm2": 28000, "axles": 2},
    {"model": "CAT DP35", "capacity_kg": 3175, "load_kN": 31.1, "wheel_load_kN": 7.78, "contact_area_mm2": 36000, "axles": 2},
    {"model": "CAT DP45", "capacity_kg": 4082, "load_kN": 40.0, "wheel_load_kN": 10.01, "contact_area_mm2": 42000, "axles": 2},
    {"model": "CAT DP55", "capacity_kg": 4989, "load_kN": 48.9, "wheel_load_kN": 12.23, "contact_area_mm2": 48000, "axles": 2},
    {"model": "CAT DP70", "capacity_kg": 6350, "load_kN": 62.3, "wheel_load_kN": 15.57, "contact_area_mm2": 54000, "axles": 2},
    {"model": "CAT DP100", "capacity_kg": 9072, "load_kN": 89.0, "wheel_load_kN": 22.25, "contact_area_mm2": 66000, "axles": 2},
    {"model": "CAT DP115", "capacity_kg": 10433, "load_kN": 102.3, "wheel_load_kN": 25.58, "contact_area_mm2": 72000, "axles": 2},
    {"model": "CAT DP135", "capacity_kg": 12247, "load_kN": 120.1, "wheel_load_kN": 30.03, "contact_area_mm2": 78000, "axles": 2},
    {"model": "CAT DP160", "capacity_kg": 14515, "load_kN": 142.4, "wheel_load_kN": 35.59, "contact_area_mm2": 84000, "axles": 2},
    {"model": "Kalmar DCG100", "capacity_kg": 4536, "load_kN": 44.5, "wheel_load_kN": 11.13, "contact_area_mm2": 50000, "axles": 2},
    {"model": "Kalmar DCG150", "capacity_kg": 6804, "load_kN": 66.7, "wheel_load_kN": 16.68, "contact_area_mm2": 62000, "axles": 2},
]

AASHTO_TRUCKS = [
    {"designation": "H-10", "gvw_kN": 44.5, "axle_load_front_kN": 8.9, "axle_load_rear_kN": 35.6},
    {"designation": "H-15", "gvw_kN": 66.7, "axle_load_front_kN": 13.3, "axle_load_rear_kN": 53.4},
    {"designation": "H-20", "gvw_kN": 89.0, "axle_load_front_kN": 17.8, "axle_load_rear_kN": 71.2},
    {"designation": "H-25", "gvw_kN": 111.2, "axle_load_front_kN": 22.2, "axle_load_rear_kN": 89.0},
    {"designation": "HS-15", "gvw_kN": 106.8, "axle_load_front_kN": 13.3, "axle_load_rear_kN": 53.4},
    {"designation": "HS-20", "gvw_kN": 142.3, "axle_load_front_kN": 17.8, "axle_load_rear_kN": 71.2},
    {"designation": "HS-25", "gvw_kN": 177.9, "axle_load_front_kN": 22.2, "axle_load_rear_kN": 89.0},
    {"designation": "HS-30", "gvw_kN": 213.5, "axle_load_front_kN": 26.7, "axle_load_rear_kN": 106.8},
]

CONVERSION_FACTORS = [
    {"from": "inches", "to": "mm", "factor": 25.4},
    {"from": "feet", "to": "m", "factor": 0.3048},
    {"from": "psi", "to": "MPa", "factor": 0.00689476},
    {"from": "MPa", "to": "psi", "factor": 145.0377},
    {"from": "pci (lb/inÂ³)", "to": "kPa/mm", "factor": 0.271447},
    {"from": "kPa/mm", "to": "pci (lb/inÂ³)", "factor": 3.6838},
    {"from": "kip", "to": "kN", "factor": 4.44822},
    {"from": "kN", "to": "kip", "factor": 0.224809},
    {"from": "lb/ftÂ³", "to": "kg/mÂ³", "factor": 16.0185},
    {"from": "kg/mÂ³", "to": "lb/ftÂ³", "factor": 0.062428},
    {"from": "lb/inÂ³", "to": "kg/mÂ³", "factor": 27679.9},
    {"from": "kg/mÂ³", "to": "lb/inÂ³", "factor": 3.613e-5},
    {"from": "Â°F", "to": "Â°C", "factor": "(Â°F - 32) / 1.8"},
    {"from": "Â°C", "to": "Â°F", "factor": "Â°C * 1.8 + 32"},
]


@router.get("/")
async def grdslab_root():
    return {
        "name": "GRDSLAB Concrete Slab on Grade Calculator",
        "version": "1.0.0",
        "endpoints": {
            "convert": "GET /api/v1/grdslab/convert?inches=X (or mm=X, psi=X, etc.)",
            "calculate": "POST /api/v1/grdslab/calculate",
            "soil-types": "GET /api/v1/grdslab/soil-types",
            "forklift-table": "GET /api/v1/grdslab/forklift-table",
            "aashto-trucks": "GET /api/v1/grdslab/aashto-trucks",
            "conversion-factors": "GET /api/v1/grdslab/conversion-factors",
        },
        "references": ["ACI 360R", "PCA Method", "Westergaard Equations"],
    }


@router.get("/convert")
async def convert(
    inches: float | None = Query(None),
    mm: float | None = Query(None),
    psi: float | None = Query(None),
    mpa: float | None = Query(None),
    pci: float | None = Query(None),
    kpa_mm: float | None = Query(None),
    kip: float | None = Query(None),
    kn: float | None = Query(None),
):
    result = {}
    if inches is not None:
        result["mm"] = round(inches * CONVERSIONS["in_to_mm"], 2)
        result["inches"] = inches
    if mm is not None:
        result["inches"] = round(mm * CONVERSIONS["mm_to_in"], 4)
        result["mm"] = mm
    if psi is not None:
        result["MPa"] = round(psi * CONVERSIONS["psi_to_MPa"], 4)
        result["psi"] = psi
    if mpa is not None:
        result["psi"] = round(mpa * CONVERSIONS["MPa_to_psi"], 2)
        result["MPa"] = mpa
    if pci is not None:
        result["kPa_mm"] = round(pci * CONVERSIONS["pci_to_kPa_mm"], 4)
        result["pci"] = pci
    if kpa_mm is not None:
        result["pci"] = round(kpa_mm * CONVERSIONS["kPa_mm_to_pci"], 4)
        result["kPa_mm"] = kpa_mm
    if kip is not None:
        result["kN"] = round(kip * CONVERSIONS["kip_to_kN"], 2)
        result["kip"] = kip
    if kn is not None:
        result["kip"] = round(kn * CONVERSIONS["kN_to_kip"], 4)
        result["kN"] = kn
    return result


@router.post("/calculate")
async def calculate(
    load_kN: float = Query(..., description="Applied load in kN"),
    thickness_mm: float = Query(..., description="Slab thickness in mm"),
    concrete_strength_MPa: float = Query(30, description="Concrete compressive strength in MPa"),
    subgrade_modulus_kPa_mm: float = Query(0.054, description="Subgrade reaction modulus in kPa/mm"),
    contact_width_mm: float = Query(200, description="Contact width (bearing area width) in mm"),
    contact_area_mm2: float = Query(40000, description="Contact area in mmÂ²"),
):
    return calculate_full(
        P_kN=load_kN,
        t_mm=thickness_mm,
        fc_MPa=concrete_strength_MPa,
        k_kPa_mm=subgrade_modulus_kPa_mm,
        b_mm=contact_width_mm,
        Ac_mm2=contact_area_mm2,
    )


@router.get("/soil-types")
async def soil_types():
    return SOIL_TYPES


@router.get("/forklift-table")
async def forklift_table():
    return FORKLIFT_TABLE


@router.get("/aashto-trucks")
async def aashto_trucks():
    return AASHTO_TRUCKS


@router.get("/conversion-factors")
async def conversion_factors():
    return CONVERSION_FACTORS
