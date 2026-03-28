# Talking P&IDs — Demo Script
### Internal guide for ZeerakLabs representatives

---

## Before the meeting

- Open the app at **talkingpnid.zeeraklabs.online** and log in (credentials provided separately)
- Have the app on a screen the client can see clearly — tablet or laptop works well
- The default loaded diagram is the **Fuel Gas KO Drum (PID-008)** — this is your primary demo diagram
- Know your audience: is this a process engineer, maintenance lead, or management? Adjust depth accordingly

---

## Opening (2 min)

Start with the problem, not the product:

> "How much time does your team spend hunting through P&ID drawings to answer questions that should take 30 seconds? A new operator asks a senior engineer — who's already busy — where the isolation valves are for a vessel. The engineer drops what they're doing, pulls up the drawing, traces the lines. Repeat that 10 times a day, across a 200-P&ID facility."

> "We built Talking P&IDs to give that time back. Every engineer on your team can query the drawings directly, in plain English, and get accurate answers instantly."

---

## Demo flow (10–12 min)

### Scene 1 — The basics: finding equipment (2 min)

Start a session. Say:

> "Let me show you the simplest thing first."

Ask: **"What are the design conditions for vessel 362-V001?"**

What to say while the answer comes:
> "This is a natural language question — no special syntax, no tag lookup, no searching. The system reads the diagram and pulls the data box from the vessel."

Point out the design pressure, design temperature, operating conditions in the answer.

---

### Scene 2 — Isolation for maintenance (3 min)

This is the money shot. Ask:

> **"What are all the isolation valves for vessel 362-V001?"**

While the answer loads:
> "This is what takes a trained engineer 20–30 minutes to do from a cold start on an unfamiliar P&ID. You have to trace every line in and out of the vessel, identify each manual isolation, check the normal position, note which ones are locked."

When the answer appears, walk through the table:
> "Here's your isolation valve list — tag, type, size, normal position. You can hand this to a technician in the field right now."

Ask a follow-up to show conversational memory:
> **"Which of those are locked open?"**

---

### Scene 3 — Troubleshooting scenario (3 min)

> "Now let's do something that shows real depth. A field engineer calls the control room: pressure is building upstream of a valve. What's happening?"

Ask: **"EZV-0002 has closed unexpectedly — what are the upstream pressure effects and what safeguards are in place?"**

While it loads:
> "This requires understanding the topology — what's upstream, what's connected, what protection exists. The system traces the process flow and identifies the safeguards: PSVs, high-pressure trips, bypasses."

Point out the ESD logic and PSV references in the answer.

---

### Scene 4 — Cross-diagram question (2 min, if time permits)

Switch to "All P&IDs" in the sidebar.

Ask: **"How does the DS-1 scraper receiver connect to the KO drum?"**

> "We have three interconnected P&IDs loaded here — two scraper receivers feeding a fuel gas knockout drum. The system understands the connections across all three drawings."

---

### Scene 5 — Hand it to them (2 min)

If the client is engaged, say:

> "What would you actually want to know about one of your P&IDs? Ask it."

Let them type a question. This is the most powerful moment in the demo — their question, their drawing type, their language.

---

## Closing (2 min)

> "What you've seen works on scanned raster P&IDs — the same format most operating facilities have. No reformatting, no CAD files, no special export. We process the PDF directly."

> "The current version is a working proof of concept on three real P&IDs from a production oil field. The next step is running this on your drawings — we'd need a set of P&IDs and a week of processing time to have a working system on your data."

> "We're offering a structured pilot to a small number of clients. You'd get access to query your own P&IDs, we'd work closely with your team to validate the answers, and you'd see exactly where the system performs and where the gaps are."

---

## Common questions and how to handle them

**"How accurate is it?"**
> "On our benchmark set of 10 engineering questions against a real P&ID, we score 79/100. The questions that score lower are ones requiring very precise component identification from dense areas of the drawing — spectacle blinds, exact spec break locations. We know exactly where the gaps are and are actively closing them. For the 80% of day-to-day questions an engineer asks, the accuracy is high."

**"What data does it need?"**
> "Just the P&ID PDFs — scanned or digital. We handle the processing. The drawings never leave a secure environment."

**"How long does it take to onboard a new P&ID set?"**
> "For a set of 10–20 P&IDs, roughly a week of processing time. We're working to bring that down."

**"Can it handle our legend and symbol standards?"**
> "The system reads your legend sheets as part of the process — it learns your specific abbreviations, valve symbols, and notation conventions from your own documents."

**"What about integration with our existing systems?"**
> "The current version is a standalone web app. API integration with plant information systems, document management, or operator workstations is on the roadmap."

---

## Leave-behinds

- Give the client the **one-pager** (client-one-pager) with the trial access URL
- Trial credentials: they get 48-hour access to the Rumaila demo environment
- Follow up within 48 hours with a note and a pilot proposal if interest is high
