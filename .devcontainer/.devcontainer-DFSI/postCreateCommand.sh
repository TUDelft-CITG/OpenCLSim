#!/bin/bash

set -e

echo ""
echo "=============================================="
echo "   OpenCLSim DfSI Environment Setup"
echo "=============================================="
echo ""

echo "Python version:"
python --version

echo ""
echo "Installing OpenCLSim in editable mode..."
# This runs inside the mounted repo workspace, where setup.py/pyproject.toml exists
python -m pip install -e .

echo ""
echo "Installing compatible OpenTNSim version..."
python -m pip install "opentnsim==1.3.7"

echo ""
echo "OpenCLSim version:"
python -c "import openclsim; print(openclsim.__version__)"

echo ""
echo "OpenTNSim version:"
python -c "import opentnsim; print(opentnsim.__version__)"

echo ""
echo "Registering Jupyter kernel..."
python -m ipykernel install --user \
    --name openclsim \
    --display-name "Python (OpenCLSim)"

echo ""
echo "=============================================="
echo "   DfSI environment ready!"
echo "=============================================="
echo ""
