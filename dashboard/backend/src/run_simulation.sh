#!/bin/bash

echo "Scenario file ${SCENARIO_FILE}"
cd /simulation
python run_scenarios.py scenario-A1.json
