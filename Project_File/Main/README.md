# ParkFlow: Smart Parking Management System

Samsung Innovation Campus (SIC 8) — Final Applied Graduation Project 
Comprehensive implementation covering Chapters 1 through 8 (OOP, Custom Data Structures, Algorithms, Pandas, and Streamlit).

---

# 1. Project Overview

ParkFlow is a modular, enterprise-grade smart parking management platform designed for modern multi-floor facilities. The application bridges hardware-inspired IoT parking sensor telemetry with an interactive software suite. It orchestrates vehicle check-in, nearest-spot allocation, live multi-floor visual occupancy, double-parked valet stack maneuvers, automated invoicing, and business intelligence analytics.

The system is built under a **Clean Modular Architecture** adhering to the principle of Separation of Concerns.

---

# 2. Architecture & Directory Structure

final project/
├── app.py                      # Master Streamlit orchestrator managing unified session state            
├── README.md                   # System documentation
│
├── models/                     # Object-Oriented Domain Entities
│   ├── vehicle.py              # Vehicle base class, subclasses (Regular, EV, Handicap), Regex validation
│   ├── parking_spot.py         # Spot entity, Manhattan distance calculation, occupancy state
│   ├── parking_lot.py          # Central parking lot manager bridging tickets and spots
│   └── ticket.py               # Digital parking ticket model with unique identifier generation
│
├── algorithms/                 # Custom Data Structures & Manual Algorithms
│   ├── stack.py                # Custom bounded Stack (LIFO) for valet parking with retrieval maneuver
│   ├── stack_ds.py             # Audit logging stack for tracking transactions and undo actions
│   ├── hash_table.py           # Custom Hash Table implementation for O(1) ticket lookups
│   ├── allocation.py           # Greedy nearest-spot allocation algorithm
│   ├── sorting.py              # Handcrafted Merge Sort and Quick Sort with comparison counters
│   └── searching.py            # Binary Search and Sequential Search algorithms
│
├── modules/                    # Streamlit User Interface Tabs
│   ├── arrival.py              # Tab 1: Vehicle check-in, plate scanner, and greedy ticket issuance
│   ├── view.py                 # Tab 2: Live 2D multi-floor visual grid & valet stack controller
│   ├── exitscreen.py           # Tab 3: Exit verification, payment gateway, and spot release
│   ├── billing.py              # Dynamic pricing engine, VAT calculation, and cash/card validators
│   └── member4_admin.py        # Tab 4: Executive dashboard, Pandas KPIs, and algorithm benchmark lab
│
├── data/                       # Real-World IoT Dataset & Analytics
│   ├── IIoT_Smart_Parking_Management.csv # Real Industrial IoT parking dataset sourced from Kaggle
│   ├── parking_history.csv     # Cleaned, transformed dataset containing 1,000 real parking sessions
│   ├── analytics_engine.py     # Pandas metrics engine (occupancy rates, revenue, rush hour surges)
│   └── generate_dataset.py     # ETL data pipeline processing Kaggle telemetry into standard schema
│
└── tests/                      # Verification & Quality Assurance
    └── testbilling.py          # Unit test suite verifying rates, caps, payments, and stack operations
```
------

# 3. End-to-End System Workflow

1.Tab 1 — Arrival & Entry:  
   The gate kiosk scans or accepts a license plate. Plate validity is checked via Regular Expressions. The Greedy Allocator determines the optimal available spot based on vehicle requirements (EV, Handicap, or Regular). A digital ticket with a timestamp is issued.

2.Tab 2 — Live 2D Multi-Floor Grid & Valet:  
   Displays the parking layout divided into Floor 1 (Priority/Ground) and Floor 2 (Upper Level). Occupied spots turn red in real time with the active plate number. The Valet Lane manages double-parked vehicles using a bounded Stack; when an inner car must be retrieved, an auxiliary stack temporarily offloads blocking vehicles and restores order.

3.Tab 3 — Exit & Checkout:
   The cashier searches by license plate or ticket ID. The billing engine calculates parking duration, applies grace periods (under 10 minutes free), incorporates hourly rates with 14% VAT, and computes rush hour multipliers ($1.5\times$). Once paid via Cash (with change return), Card (16-digit validation), or Mobile Wallet, the spot is automatically vacated and reset to green.

4.Tab 4 — Admin Intelligence & Algorithm Lab:
   Executives monitor total revenue, occupancy trends, peak hours, and turnover rates computed from 1,000 real IoT records. The Algorithm Lab allows benchmarking of manual Merge Sort vs Quick Sort on financial fields.


```
