# Comprehensive P&ID Summary
## Fuel Gas KO Drum PP01-362-V001

**Drawing Number:** 100478CP-N-PG-PP01-PR-PID-0008-001  
**Revision:** C02 (01.09.16 — Issued for Construction)  
**Project:** Early Power Plant, Rumaila Oil Field  
**Contract:** 100478  
**Engineering:** CPECC / CH2M Hill

---

## 1. Equipment Overview

### Primary Vessel: PP01-362-V001 (Fuel Gas Knockout Drum)

| Parameter | Value |
|-----------|-------|
| Size | 2200mm (I.D.) × 5500mm (L) |
| Design Pressure | 14 barg / FV |
| Design Temperature | -20 to 100°C (NOTE-7) |
| Operating Pressure | 9.0–10.4 barg |
| Operating Temperature | 23–72°C |
| Material | Carbon Steel (CS) + 3mm CA |
| Insulation | None (CO2 service) |

The KO drum serves as a liquid knockout separator for fuel gas streams from two upstream scrapper receivers (DS-1 and DS-3). It removes entrained liquids before the gas proceeds to the Fuel Gas Treatment Package.

---

## 2. Component Summary Statistics

| Category | Count |
|----------|-------|
| **Vessel** | 1 |
| **Nozzles** | 19 |
| **Valves (HV series)** | 52 |
| **Pressure Safety Valves (PSV)** | 2 |
| **Pressure Instruments (PI/PIT/PZT/PIC/PG)** | 10 |
| **Level Instruments (LI/LIT/LG/LIC/LV/LZT)** | 15 |
| **Other Instruments (ZI/ZT/FO/CIT/CE/CI)** | 8 |
| **Logic/Voting Blocks** | 2 |
| **Reducers** | 8 |
| **Spectacle Blinds (SPK)** | 2 |
| **Named Pipe Lines** | 22+ |

---

## 3. Process Flow Description

### 3.1 Fuel Gas Inlet System

Two parallel 16" fuel gas inlet streams enter the drum:

1. **DS-1 Line:** `16"-PP01-361-GF0014-B03F9-PP`
   - Source: DS-1 Scrapper Receiver (N-PG-PP01-PR-PID-0005-001)
   - Route: HV0094 → 16"×12" reducer → HV0093 → N4

2. **DS-3 Line:** `16"-PP01-361-GF0031-B03F9-PP`
   - Source: DS-3 Scrapper Receiver (N-PG-PP01-PR-PID-0007-001)
   - Route: HV0203 → 16"×12" reducer → HV0095 → N5

**Key Requirements:**
- Both lines marked "NO POCKETS" (NOTE-10) to prevent liquid accumulation
- Both inlet nozzles (N4, N5) have spectacle blinds per NOTE-2

### 3.2 Fuel Gas Outlet System

The treated fuel gas exits via:
- **Nozzle N2** (16") → `16"-PP01-362-GF0002-B01E9-PP`
- **Destination:** Fuel Gas Treatment Package (N-PG-PP01-PR-PID-0009-001)

### 3.3 Pressure Relief System (HP Flare)

Dual redundant PSV trains protect against overpressure:

| Component | Set Pressure | Size | Inlet | Outlet |
|-----------|-------------|------|-------|--------|
| PSV-0001 | 14.0 barg | 8T10 | 14"×8" reducer | 16"×10" reducer |
| PSV-0002 | 14.0 barg | 8T10 | 14"×8" reducer | 16"×10" reducer |

**Design Case:** DS-3 PCV Failure

**Isolation Philosophy:**
- Inlet: HV0004/HV0006 (ILO - Indicated Locked Open) with SPK-0001 spectacle blinds
- Bypass: HV0005/HV0007 (1" bypass valves)
- Outlet: HV0038/HV0039 and HV0040/HV0041 (ILO pairs)

All PSV discharges route to HP Flare Header (N-PG-PP01-PR-PID-0021-001) with 1:500 slope.

### 3.4 Condensate/Liquid Outlet System

Separated liquids drain via:
- **Nozzle N3** (3") → HV0002 → 4"-PP01-512-PK0005-C01N8-PP
- Level control via LIC-0001 → LV-0001
- Emergency shutdown via EZV-0001
- Final destination: Condensate Storage Vessel (N-PG-PP01-PR-PID-0024-001)

**Two-Phase Line:** 4"-PP01-512-PK0006-B01M8-PP with 1:250 slope (NOTE-10)

---

## 4. Safety Instrumented Systems

### 4.1 High Pressure Shutdown (2oo3 Voting)

**Logic Block:** 362-004

| Transmitter | Nozzle | Isolation |
|-------------|--------|-----------|
| PZT-0001A | N13 | HV0011 (LO) |
| PZT-0001B | N14 | HV0012 (LO) |
| PZT-0001C | N15 | HV0013 (LO) |

- Three redundant pressure transmitters feed 2-out-of-3 voting logic
- Consistent with SIL-rated shutdown function
- Associated indicators: PI-0001A/B/C (with HH alarms)

### 4.2 Level Shutdown (2oo3 Voting)

**Logic Block:** 362-003-007

| Transmitter | Type | Function |
|-------------|------|----------|
| LZT-0002A | GWR (Guided Wave Radar) | Primary level |
| LZT-0002B | GWR | Redundant |
| LZT-0002C | GWR | Redundant |

- 2oo3 voting prevents spurious trips while ensuring reliable shutdown
- Equalization/isolation via HV0042, HV0044 for online maintenance
- Local indicators: LI-0002A/B/C (with HH/LL alarms)

### 4.3 Level Control Loop

```
LIT-0001 (N7A/N7B) → LIC-0001 → LV-0001 (drain control)
                          ↓
                     EZV-0001 (emergency shutdown)
```

- LIC-0001 has H/L alarm setpoints
- EZV-0001 associated with 362-I-007 interlock

### 4.4 Pressure Control Loop

```
PIT-0002 (N16) → PIC-0002 → PV0002
                     ↓
              ZT0002/ZI0002 (position feedback)
```

- NOTE-11: Discrepancy alarm when position feedback differs from controller output by >10%
- PV0002 discharges to HP Flare via 10"-PP01-500-VK0010-B01B8

---

## 5. Instrumentation Architecture

### 5.1 Level Measurement

| Tag | Type | Connection | Notes |
|-----|------|------------|-------|
| LIT-0001 | Level Indicating Transmitter | N7A/N7B | Main control |
| LIT-0003 | Level Indicating Transmitter | N10A | Secondary |
| LG-0001 | Level Glass (Sight Glass) | N18A/N18B | Local visual |
| LZT-0002A/B/C | GWR Level Transmitter | N6A/N6B | Safety (2oo3) |
| LI-0002A/B/C | Level Indicator | - | HH/LL alarms |
| LI-0003 | Level Indicator | N15 | Local |

### 5.2 Pressure Measurement

| Tag | Type | Connection | Notes |
|-----|------|------------|-------|
| PZT-0001A/B/C | Safety Pressure Transmitter | N13/N14/N15 | 2oo3 voting |
| PIT-0002 | Pressure Indicating Transmitter | N16 | Control loop |
| PIC-0002 | Pressure Controller | - | H/L alarms |
| PI-0001A/B/C | Pressure Indicator | - | HH alarms |
| PG-0001 | Pressure Gauge | - | Local |

### 5.3 Conductivity Measurement

| Tag | Type | Location |
|-----|------|----------|
| CE-0001 | Conductivity Element | Condensate outlet |
| CIT-0001 | Conductivity Transmitter | Condensate outlet |
| CI-0001 | Conductivity Indicator | Local panel |

Purpose: Monitor water/hydrocarbon quality before routing to Condensate Storage Vessel

---

## 6. Valve Summary by Function

### 6.1 Inlet Isolation
- HV0094, HV0203: 16" main inlet isolation
- HV0093, HV0095: 12" nozzle isolation (with spectacle blinds)

### 6.2 PSV Train Isolation
- HV0004, HV0006: PSV inlet isolation (ILO FB)
- HV0005, HV0007: 1" bypass valves
- HV0038, HV0039, HV0040-PSV, HV0041-PSV: PSV outlet isolation (ILO)

### 6.3 Instrument Isolation
- HV0011–HV0014: Pressure transmitter isolation (all LO)
- HV0022–HV0030: Level instrument isolation
- HV0034: Level transmitter isolation (LO)
- HV0040-LZT through HV0045: GWR transmitter isolation/equalization

### 6.4 Drain/Vent Control
- HV0002: Vent/drain isolation
- HV0016–HV0021: PV0002 bypass/isolation arrangement
- HV0018, HV0019: 4" drain (LC - Locked Closed)
- HV0028-DRAIN: Liquid drain control valve
- HV0052, HV0056: Condensate drain

### 6.5 Utility Connections
- HV0001, HV0051, HV0002-UC: Utility connection train (NC)

---

## 7. Piping Specifications

| Spec Code | Application |
|-----------|-------------|
| B01B8 | Flare/vent lines (high temp service) |
| B01E9 | Process fuel gas lines |
| B03F9 | Fuel gas inlet/instrument lines |
| B01M8 | Drain/sample lines at grade |
| C01N8 | Condensate drain header |
| C01N9 | Vent line spec variant |

**Spec Breaks Noted:**
- B01B8 ↔ B01E9 at PSV inlet/outlet transitions
- B03F9 → B01M8 at drain line exits to grade
- B01E9 ↔ C01N9 at vent/drain transitions

---

## 8. External Drawing References

| Drawing | Description | Connection |
|---------|-------------|------------|
| N-PG-PP01-PR-PID-0005-001 | DS-1 Scrapper Receiver | 16" inlet GF0014 |
| N-PG-PP01-PR-PID-0007-001 | DS-3 Scrapper Receiver | 16" inlet GF0031 |
| N-PG-PP01-PR-PID-0009-001 | Fuel Gas Treatment Package | 16" outlet GF0002 |
| N-PG-PP01-PR-PID-0021-001 | HP Flare Header | All relief/blowdown |
| N-PG-PP01-PR-PID-0024-001 | Condensate Storage Vessel | Condensate outlet |

---

## 9. Key Design Notes

| Note | Description |
|------|-------------|
| NOTE-2 | Spectacle blind/flange requirement on inlet nozzles N4, N5 |
| NOTE-5 | Drain/sample station specification |
| NOTE-7 | Adiabatic depressurization temperature consideration (-20°C) |
| NOTE-8 | Spectacle blind orientation on PSV inlet trains |
| NOTE-10 | NO POCKETS requirement for all condensate-laden lines |
| NOTE-11 | PV0002 position discrepancy alarm (>10% deviation) |
| NOTE-12 | FC TSO TYPE-C 300# valve specification |
| NOTE-13 | Condensate outlet specification |

---

## 10. Critical Observations & Flags

### 10.1 Duplicate Tag Concerns
- **HV0028** appears on both instrument isolation (upper) AND drain control (lower) — verify against drawing legend
- **HV0040/HV0041** used for both PSV-0002 outlet isolation AND LZT transmitter isolation — likely different valves requiring clarification
- **HV0031/HV0032** appear as dual instances — verify intended usage

### 10.2 Safety-Critical Features
- All instrument take-offs use 2" LO (Locked Open) valves for continuous sensing availability
- Dual PSV trains with full redundancy and ILO isolation
- 2oo3 voting on both pressure and level safety functions (SIL requirement)
- Multiple IG/CO2 purge points for safe maintenance isolation

### 10.3 Low Temperature Service
- Vessel rated for -20°C minimum (NOTE-7 - adiabatic depressurization)
- "LOW TEMP." annotation on flare/blowdown lines
- Material spec transitions at appropriate service boundaries

### 10.4 Gravity Drainage Requirements
- Inlet lines: NO POCKETS (NOTE-10)
- Condensate outlet: 1:250 slope
- Flare lines: 1:500 slope

---

## 11. Deduplication Notes

The following components were identified as duplicates across tile overlaps and merged:

| Component | Appeared In | Resolution |
|-----------|-------------|------------|
| N4, N5 | r1c1, r2c1 | Merged - same inlet nozzles |
| N17 | r1c1, r2c1, r2c2 | Merged - single nozzle |
| PZT-0001A/B/C | r1c2, r2c2 | Merged - tile overlap |
| PIT-0002 | r1c2, r2c2 | Merged - tile overlap |
| LG-0001 | r2c1, r2c2 | Merged - same level gauge |
| HV0024, HV0025 | r2c1, r2c2 | Merged - same bridle valves |
| LZT-0002A/B/C | r1c3, r2c2, r2c3 | Merged - same GWR transmitters |

---

*Document generated from tile analysis of drawing 100478CP-N-PG-PP01-PR-PID-0008-001*
