K_PA_MM = 0.054
PSI_MPA = 0.00689476
MPA_PSI = 145.0377
IN_MM = 25.4
MM_IN = 1 / 25.4
PCI_KPA_MM = 0.271447
KPA_MM_PCI = 1 / 0.271447
KIP_KN = 4.44822
KN_KIP = 1 / 4.44822
LB_IN3_KG_M3 = 27.6799
KG_M3_LB_IN3 = 1 / 27.6799

SLAB_THICKNESS_IN = 8
SLAB_THICKNESS_MM = SLAB_THICKNESS_IN * IN_MM
CONCRETE_STRENGTH_PSI = 4000
CONCRETE_STRENGTH_MPA = CONCRETE_STRENGTH_PSI * PSI_MPA
SUBGRADE_PCI = 100
SUBGRADE_KPA_MM = SUBGRADE_PCI * PCI_KPA_MM

CONVERSION_FACTORS = {
    "1 inch": f"{IN_MM} mm",
    "1 mm": f"{MM_IN:.4f} inches",
    "1 psi": f"{PSI_MPA:.6f} MPa",
    "1 MPa": f"{MPA_PSI:.2f} psi",
    "1 pci": f"{PCI_KPA_MM:.6f} kPa/mm",
    "1 kPa/mm": f"{KPA_MM_PCI:.4f} pci",
    "1 kip": f"{KIP_KN:.2f} kN",
    "1 kN": f"{KN_KIP:.4f} kip",
    "1 lb/in³": f"{LB_IN3_KG_M3:.4f} kg/m³",
    "1 kg/m³": f"{KG_M3_LB_IN3:.6f} lb/in³",
}

TYPICAL_VALUES = {
    "slab_thickness_inches": SLAB_THICKNESS_IN,
    "slab_thickness_mm": round(SLAB_THICKNESS_MM, 1),
    "concrete_strength_psi": CONCRETE_STRENGTH_PSI,
    "concrete_strength_MPa": round(CONCRETE_STRENGTH_MPA, 2),
    "subgrade_modulus_pci": SUBGRADE_PCI,
    "subgrade_modulus_kPa_mm": round(SUBGRADE_KPA_MM, 3),
}
