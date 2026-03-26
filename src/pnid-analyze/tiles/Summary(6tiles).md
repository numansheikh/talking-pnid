# Summary of All Tiles


**Summary of findings for tile r1c1:**

| Category | Count |
| ----- | ----- |
| Valves (HV) | 4 (HV0094, HV0203, HV0093, HV0095) |
| Nozzles | 3 (N4, N5, N17-partial) |
| Reducers | 2 (16"×12") |
| Line Numbers | 2 (GF0014, GF0031) |
| Source References | 2 (DS-1 & DS-3 P\&IDs) |
| Annotations/Notes | 3 (NOTE-2, NOTE-10, vessel data block) |

Key observations:

* Both 16" inlet lines carry **no-pocket** routing requirements (NOTE-10), typical for condensate-laden fuel gas to prevent liquid accumulation  
* Both inlets reduce 16"→12" before entering the drum top nozzles N4 and N5  
* The KO drum (PP01-362-V001) body is only partially visible — its full representation continues into adjacent tiles

**Summary of findings for tile r1c2:**

| Category | Count |
| ----- | ----- |
| Pressure Safety Valves (PSV) | 2 (PSV-0001, PSV-0002) |
| Isolation/Block Valves (HV) | 12 (HV0004, HV0005, HV0006, HV0007, HV0038, HV0039, HV0040, HV0041, HV0011, HV0012, HV0013, HV0014) |
| Pressure Instruments (PI/PIT/PZT/PIC/PG) | 10 (PI-0001A/B/C ×2 rows, PZT-0001A/B/C, PIT-0002, PIC-0002, PG-0001) |
| Reducers | 4 (two 14″×8″ inlet, two 16″×10″ outlet) |
| Spectacle Blinds (SPK) | 2 (SPK-0001 left & right trains) |
| Logic/Voting Blocks | 1 (362-004, 2oo3 voting) |
| Line Numbers | 2 (GF0001-B01E9-PP @14″, GF0004-B01E9-PP @14″) |
| Nozzles | 7 (N1, N2, N6A, N13, N14, N15, N16) |
| Annotations/Notes | 2 (NOTE-8, B01B8/B01E9 spec break) |

**Key observations:**

* **Dual PSV relief train** — PSV-0001 and PSV-0002 are identically configured in parallel, both set at **14.0 barg** for the DS-3 PCV failure case, sized 8T10, with 14″×8″ inlet reducers and 16″×10″ outlet reducers discharging to the flare header at the top of the tile  
* **2oo3 voting logic (362-004)** — Three redundant pressure transmitters (PZT-0001A/B/C) feed a two-out-of-three safety voting block, consistent with a **SIL-rated high-pressure shutdown** function; the PI-0001A/B/C indicators are duplicated in two rows suggesting local and DCS/SIS parallel signal paths  
* **All instrument take-offs are 2″ LO (Locked Open)** — HV0011 through HV0015 are all locked-open block valves on instrument nozzles N13–N16, ensuring continuous pressure sensing availability  
* **PIC-0002** receives input from PIT-0002 and shows H/L alarm setpoints, likely driving a pressure control valve visible in the adjacent right tile (r1c3)  
* **Vessel body is not visible** in this tile — only nozzles (N1, N2, N6A, N13–N16) appear at the bottom boundary, confirming the KO drum shell is represented in tile r2c2 below  
* Both PSV discharge trains include **ILO (Indicated Locked Open) paired isolation valves** (HV0038/HV0039 and HV0040/HV0041), a standard safety requirement to maintain relief path availability while allowing maintenance isolation

**Key Observations for this tile (r1c3 — top-right / notes region):**

| Area | Summary |
| ----- | ----- |
| **Upper left** | Four separate HP Flare Header tie-in lines (16", 16", 8", 10") all routing to drawing N-PG-PP01-PR-PID-0021-001, all with 1:500 slope and NO POCKETS |
| **Mid left** | HV0092, 8"×6" reducer, FO0002, BDZV0001 cluster with LOW TEMP. service and 600mm MIN. spacing requirement |
| **Center** | ZI0002 / ZT0002 position measurement pair in NOTE-11 box; PV0002 control valve with 8"×10" expander |
| **Lower center** | HV0016–HV0021 isolation/bypass arrangement around PV0002; spec breaks B01B8↔B01E9 |
| **Bottom** | 16" fuel gas outlet to Treatment Package; LZT0002B/C GWR level transmitters; HV0044 |
| **Right half** | NOTES, GENERAL NOTES, and HOLDS text blocks — non-P\&ID content |

**Key observations and flags for r2c1 tile:**

| Finding | Detail |
| ----- | ----- |
| **Level Gauge Bridle** | LG-0001 is served by a full bridle: N18A → HV0024 (top, XO) → LG-0001 → HV0025 (bottom, XO) → N18B |
| **Utility Connection Train** | Complex valve train: UC → SPHN-0030 → 2"×0.75" reducer → HV0001 → HV0051 → HV0002 (NC) → N9 on line 2"-PP01-567-GF0002-B03F9 |
| **Spec Break** | B03F9 → B01M8 occurs mid-drain-line; verify material class change is intentional |
| **CO2 markers** | Appear at multiple instrument/valve locations — cross-reference with drawing legend to confirm meaning (chemical injection vs. commissioning) |
| **NOTE-2** | Referenced on both N4 and N5 blinds — note text not visible in this tile; should be captured from title block tile |
| **Drain to Grade** | 1"-PP01-512-PK0076 terminates at grade with MIN. dimension — confirm open drain compliance |

**Summary of key observations for r2c2 tile:**

| Category | Count |
| ----- | ----- |
| Instruments | 13 (LIT×2, LI, LG, LIC, LV, EZV, PZT×3, PIT, LZT×2) |
| Valves (HV series) | 30+ hand/control valves |
| Vessel nozzles | 20 (N1–N18B) |
| Named pipe lines | 6 distinct line numbers |
| Annotations/notes | 10+ |

**Key flags:**

* **HV0028 appears to be used on two separate valves** (instrument isolation upper area AND drain control lower area) — verify against title block legend or adjacent tiles.  
* **HV0031/HV0032 also appear as dual instances** — same concern.  
* The **vessel 362-V001** boundary is implied (dashed outline NOTE-9); the actual vessel shell is in the center tile (r1c2/r2c2 overlap zone).  
* **B03F9 → B01M8 spec breaks** are consistently marked at all 1" sample/drain line exits with IG (Isolation Group) and CO2 fire suppression symbols.

## **Summary of findings for tile r2c3:**

| Category | Count |
| ----- | ----- |
| Valves (HV) | 8 (HV0040, HV0041, HV0042, HV0043, HV0044, HV0045, HV0052, HV0056) |
| Instruments (LZT/LI) | 9 (LZT-0002A/B/C, LI-0002A/B/C ×2 rows) |
| Instruments (CIT/CE/CI) | 3 (CIT-0001, CE-0001, CI-0001) |
| Logic Blocks | 1 (2oo3 voting block — 362/003/007) |
| Line Numbers | 5 (PK0080, PK0081, PK0006, GF0002-partial, PID-0009 ref) |
| Destination References | 2 (PID-0009-001, PID-0024-001) |
| Utility Connections | Multiple IG & CO2 taps (≥5 each) |
| Annotations/Notes | 4 (NOTE-10, NOTE-13, scale 1:250, TWO PHASE label) |
| Title Block | 1 (full drawing title block with revision history) |

---

## **Key observations:**

* **Triple redundant GWR level measurement** — LZT-0002A/B/C are Guided Wave Radar transmitters arranged in a 2-out-of-3 (2oo3) voting logic configuration, a safety-critical SIL arrangement to trigger level shutdown only on confirmed consensus, avoiding spurious trips  
* **Isolation & equalization architecture** — each GWR transmitter pair is bridged by an HV valve (HV0042, HV0044) with individual isolation on each leg (HV0040, HV0041), enabling online maintenance without taking the full measurement loop out of service  
* **Six local level indicators (LI-0002A/B/C, two rows)** likely represent two independent sets of gauge glasses or visual indicators aligned with the upper and lower vessel chambers, correlating with HH/LL alarm setpoints visible on each symbol  
* **Condensate outlet instrumentation** — CIT-0001 with CE-0001 monitors conductivity of the condensate stream leaving the drum, critical for detecting water/hydrocarbon quality before routing to the Condensate Storage Vessel (PID-0024-001)  
* **4" two-phase condensate line** (PK0006) carries a 1:250 slope requirement (NOTE-10), consistent with gravity-draining a two-phase stream to prevent liquid hold-up — same NOTE-10 seen in tile r1c1 on the inlet lines  
* **Multiple IG/CO2 utility purge points** around the HV valve cluster indicate this section requires inert purging capability, typical for a hydrocarbon drain/vent header where safe isolation and purging before maintenance is mandatory  
* **Title block confirms** drawing number `100478CP-N-PG-PP01-PR-PID-0008-001`, revision **C02 (01.09.16 — Issued for Construction)**, project: Early Power Plant, Rumaila Oil Field, Contract 100478 — engineered by **CPECC** and **CH2M Hill**
