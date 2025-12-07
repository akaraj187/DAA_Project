#!/bin/bash
echo "Compiling Fraud Engine..."
g++ -o fraud_engine.exe fraud_engine.cpp
if [ $? -eq 0 ]; then
    echo "Compilation Successful."
    echo "Run the backend with: python app.py"
else
    echo "Compilation Failed!"
    exit 1
fi
