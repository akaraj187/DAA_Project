# Transaction Fraud Detection System - Project Documentation

## Overview
This project is a full-stack fraud detection system that integrates a Python web interface with a high-performance C++ analysis engine. It utilizes advanced data structures and algorithms (Trie, Hash Map, KMP) to detect suspicious patterns in financial transactions.

## System Architecture & Data Flow

### 1. User Input (Frontend)
- **Interface:** The user interacts with the dashboard (`index.html`).
- **Input Method:** Transactions are entered into a text area in CSV format (e.g., `1001,500,Offshore Payment`).
- **Trigger:** Clicking "Run Detection Engine" executes the JavaScript `analyzeTransactions()` function.
- **Payload:** The input text is packaged into a JSON object (`{ "data": "..." }`) and sent to the backend via a POST request.

### 2. Data Transfer (Middleware)
- **Server:** A Python Flask server (`app.py`) handles the request at the `/analyze` endpoint.
- **Process Management:** Python spawns the C++ executable (`fraud_engine`) as a subprocess using the `subprocess` module.
- **Input Pipe:** The raw transaction text is piped directly into the C++ program's Standard Input (`stdin`).

### 3. C++ Analysis Engine (`fraud_engine.cpp`)
The C++ engine serves as the core processing unit, executing three distinct algorithms to identify potential fraud.

#### Phase A: Parsing & Pre-processing
- Reads input from `stdin` line-by-line.
- Parses CSV data to extract **ID**, **Amount**, and **Description**.
- Populates a `frequencyMap` (Hash Map) to track transaction counts per User ID.

#### Phase B: Detection Algorithms

**1. Trie (Prefix Tree) - Blacklist Verification**
- **Purpose:** Instant lookup of known malicious IDs.
- **Mechanism:** A Trie structure is pre-loaded with blacklisted IDs (e.g., "9999", "1001"). The system traverses this tree with the current transaction ID.
- **Advantage:** Provides efficient prefix-based matching and fast lookups, independent of the blacklist size.

**2. Hash Map (Frequency Map) - Velocity Check**
- **Purpose:** Detect high-frequency transaction spamming.
- **Mechanism:** Utilizes the pre-calculated `frequencyMap`. If a User ID's occurrence count exceeds a threshold (e.g., > 3), it is flagged as "High Frequency Fraud".
- **Advantage:** Offers O(1) constant time complexity for lookups, ensuring speed regardless of the dataset size.

**3. KMP (Knuth-Morris-Pratt) - Pattern Matching**
- **Purpose:** Identify suspicious keywords within transaction descriptions (e.g., "crypto", "offshore", "bet").
- **Mechanism:** Implements the KMP algorithm, which utilizes an LPS (Longest Prefix Suffix) array. This allows the search to skip unnecessary comparisons upon mismatch.
- **Advantage:** Significantly more efficient than brute-force string searching, especially for longer text descriptions, avoiding redundant checks.

### 4. Output Generation & Rendering
- **Serialization:** The C++ engine constructs a JSON string representing the analysis results (e.g., `[{"id": "1001", "is_suspicious": true, ...}]`).
- **Output:** The JSON string is printed to Standard Output (`stdout`).
- **Response:** Python captures this output and returns it to the frontend.
- **Visualization:** JavaScript parses the response and dynamically updates the UI, highlighting suspicious transactions in red and safe ones in green based on the `is_suspicious` flag.
