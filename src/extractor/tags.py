"""
P&ID tag type registries and compiled regex patterns.

Covers ISA 5.1 instrument codes and common valve/actuator codes.
Used by extract.py to identify and classify tagged items on a drawing.
"""

import re

# ── Valve types ───────────────────────────────────────────────────────────────

VALVE_TYPES: dict[str, str] = {
    # Shutdown / safety — ordered longest-first within group
    "ESDV": "Emergency Shutdown Valve",
    "EZV":  "ESD Zone Valve",
    "SDV":  "Shutdown Valve",
    "BDV":  "Blowdown Valve",
    "PSV":  "Pressure Safety Valve",
    "PRV":  "Pressure Relief Valve",
    # Control
    "TCV":  "Temperature Control Valve",
    "LCV":  "Level Control Valve",
    "FCV":  "Flow Control Valve",
    "PCV":  "Pressure Control Valve",
    # Actuated
    "MOV":  "Motor Operated Valve",
    "XV":   "Actuated Valve (On/Off)",
    # Manual / isolation
    "BFV":  "Butterfly Valve",
    "GLV":  "Globe Valve",
    "NRV":  "Non-Return Valve (Check Valve)",
    "CSE":  "Check Valve",
    "HV":   "Hand Valve (Manual)",
    "BV":   "Ball Valve",
    "GV":   "Gate Valve",
    # Generic control
    "PV":   "Process / Control Valve",
    "FV":   "Flow Valve",
    "LV":   "Level Valve",
    "TV":   "Temperature Valve",
}

# ── Instrument types (ISA 5.1) ────────────────────────────────────────────────
# Within each measured variable group, longer codes are listed first so the
# regex alternation matches PAHH before PAH, PALL before PAL, etc.

INSTRUMENT_TYPES: dict[str, str] = {
    # Pressure
    "PAHH": "Pressure Alarm High High",
    "PALL": "Pressure Alarm Low Low",
    "PAH":  "Pressure Alarm High",
    "PAL":  "Pressure Alarm Low",
    "PDT":  "Pressure Differential Transmitter",
    "PDI":  "Pressure Differential Indicator",
    "PIC":  "Pressure Indicator Controller",
    "PIT":  "Pressure Indicator Transmitter",
    "PZT":  "Pressure Transmitter (Zone)",
    "PT":   "Pressure Transmitter",
    "PI":   "Pressure Indicator",
    "PS":   "Pressure Switch",
    # Temperature
    "TAHH": "Temperature Alarm High High",
    "TALL": "Temperature Alarm Low Low",
    "TAH":  "Temperature Alarm High",
    "TAL":  "Temperature Alarm Low",
    "TIC":  "Temperature Indicator Controller",
    "TIT":  "Temperature Indicator Transmitter",
    "TT":   "Temperature Transmitter",
    "TI":   "Temperature Indicator",
    "TS":   "Temperature Switch",
    "TE":   "Temperature Element (Thermowell)",
    "TW":   "Thermowell",
    # Flow
    "FAHH": "Flow Alarm High High",
    "FALL": "Flow Alarm Low Low",
    "FAH":  "Flow Alarm High",
    "FAL":  "Flow Alarm Low",
    "FIC":  "Flow Indicator Controller",
    "FIT":  "Flow Indicator Transmitter",
    "FT":   "Flow Transmitter",
    "FI":   "Flow Indicator",
    "FQ":   "Flow Totalizer",
    "FE":   "Flow Element",
    "FS":   "Flow Switch",
    # Level
    "LAHH": "Level Alarm High High",
    "LALL": "Level Alarm Low Low",
    "LAH":  "Level Alarm High",
    "LAL":  "Level Alarm Low",
    "LIC":  "Level Indicator Controller",
    "LIT":  "Level Indicator Transmitter",
    "LT":   "Level Transmitter",
    "LI":   "Level Indicator",
    "LG":   "Level Gauge / Glass",
    "LS":   "Level Switch",
    "LE":   "Level Element",
    # Analysis
    "AIC":  "Analyzer Indicator Controller",
    "AT":   "Analyzer Transmitter",
    "AI":   "Analyzer Indicator",
    "AS":   "Analyzer Switch",
    # Position / valve position feedback
    "ZIC":  "Position Indicator Controller",
    "ZT":   "Position Transmitter",
    "ZI":   "Position Indicator",
    "ZS":   "Position Switch (Limit Switch)",
    # Speed / rotation
    "SSHH": "Speed Switch High High",
    "SSH":  "Speed Switch High",
    "ST":   "Speed Transmitter",
    "SI":   "Speed Indicator",
    "SE":   "Speed Element",
    "SS":   "Speed Switch",
    # Vibration
    "VT":   "Vibration Transmitter",
    "VI":   "Vibration Indicator",
    "VS":   "Vibration Switch",
    # Density
    "DT":   "Density Transmitter",
    "DI":   "Density Indicator",
    # Weight / force
    "WT":   "Weight Transmitter",
    "WI":   "Weight Indicator",
    # Electrical / power
    "EIT":  "Current Indicator Transmitter",
    "JT":   "Power Transmitter",
    # Multivariable
    "UT":   "Multivariable Transmitter",
    "UI":   "Multivariable Indicator",
    # Control / compute
    "YIC":  "Control Station",
}

# ── Combined registry ─────────────────────────────────────────────────────────
# Valves take precedence for shared codes (e.g. HV stays "Hand Valve").

ALL_TYPES: dict[str, str] = {**INSTRUMENT_TYPES, **VALVE_TYPES}

VALVE_CODES: frozenset[str] = frozenset(VALVE_TYPES)
INSTRUMENT_CODES: frozenset[str] = frozenset(INSTRUMENT_TYPES)


def tag_category(code: str) -> str:
    """Return 'valve', 'instrument', or 'unknown' for a given type code."""
    c = code.upper()
    if c in VALVE_CODES:
        return "valve"
    if c in INSTRUMENT_CODES:
        return "instrument"
    return "unknown"


# ── Compiled regex patterns ───────────────────────────────────────────────────
# Prefixes sorted longest-first so longer codes (ESDV, PAHH) match before
# shorter overlapping ones (ESD, PAH, PA).

_PREFIX_PATTERN = "|".join(sorted(ALL_TYPES, key=len, reverse=True))

# Matches: HV-0059  HV0059  PT-0012  FIT-0002  PV-1011/2011
TAG_RE = re.compile(
    rf"\b({_PREFIX_PATTERN})[- ]?(\d{{3,6}}(?:[/\\]\d{{3,6}})?[A-Z]?)\b",
    re.IGNORECASE,
)

# Pipe line number: size"-PPxx-system-tag-spec  e.g. 20"-PP01-361-GF0002-B03F9
LINE_RE = re.compile(
    r'\b(\d{1,3}")-?(PP\d+)-(\d{3,4})-([A-Z]{2}\d{4})-([A-Z0-9]+)\b',
    re.IGNORECASE,
)
