# Medical Billing & Claims Agent

## Overview

Healthcare billing and insurance claims processing is complex, error-prone, and slow, involving extensive manual data entry and communication. This project presents an **agentic AI multi-agent system** designed to automate the entire claims lifecycle, improving accuracy and efficiency while saving millions for healthcare providers and insurers.

Using Google Gemini's advanced multimodal AI capabilities, the system operates with autonomy and reasoning ability across multiple specialized agents:

- **Data Ingestion Agent:** Extracts critical patient and billing information from scanned medical records (images, PDFs, or text) using Gemini’s multimodal AI.
- **Claims Generation Agent:** Validates extracted data against billing rules and insurance requirements, autonomously generating the correct claim form.
- **Communication Agent:** (Future extension) Submits claims, manages follow-ups, and drafts appeal letters for denied claims using intelligent reasoning.
- **Payment Reconciliation Agent:** (Future extension) Compares received payments against claims and flags discrepancies for human review.

## Why This Matters

Manual medical billing is costly, error-prone, and leads to frequent claim denials. Automating with agentic AI not only increases speed and accuracy but also enables autonomous reasoning — such as generating complex appeals — beyond just filling forms. This multi-agent collaboration exemplifies sophisticated agentic behavior with tangible financial and operational impact.

## MVP Scope

For hackathon/demo purposes, the MVP includes two key agents:

1. **Data Ingestion Agent**
   - Upload medical bills (PDF, image, or text)
   - Extract patient name, service dates, medical codes, and amounts

2. **Claims + Appeal Agent**
   - Validate data against a simple hardcoded or JSON-based insurance ruleset
   - Generate a valid claim form if compliant
   - Autonomously generate a denial appeal letter if invalid  
   
This MVP showcases core agentic behaviors: autonomous data extraction, rule-based validation, reasoning, and multi-step decision-making.

## Tech Stack

- Python 3
- Google Gemini API (multimodal AI & LLM)
- Streamlit for fast front-end demo
- JSON for mock knowledge base and rule storage

## How to Run

1. Clone this repository
2. Set up Python environment:  
