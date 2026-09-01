#!/bin/bash

set -e

echo ""
echo "=============================================="
echo " Setting up OpenCLSim student environment"
echo "=============================================="
echo ""

python --version

echo ""
echo "Upgrading pip..."
python -m pip install --upgrade pip

echo ""
echo "Installing OpenCLSim and notebook dependencies..."

python -m pip install -e ".[testing]"

echo ""
echo "Registering Jupyter kernel..."

python -m ipykernel install --user \
    --name openclsim \
    --display-name "Python (OpenCLSim)"

echo ""
echo "=============================================="
echo " OpenCLSim environment is ready!"
echo "=============================================="
echo ""