#!/usr/bin/env bash
# Exit on error
set -o errexit

# 1. Install Python Dependencies
pip install -r requirements.txt

# 2. Compile C++ Engine using g++ (available on Render Linux env)
echo "Compiling C++ Fraud Engine..."
g++ -o fraud_engine fraud_engine.cpp

echo "Build complete."
