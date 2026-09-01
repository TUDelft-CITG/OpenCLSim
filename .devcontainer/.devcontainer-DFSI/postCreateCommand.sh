#!/bin/bash

set -e

echo ""
echo "=============================================="
echo "   OpenCLSim DfSI Environment"
echo "=============================================="
echo ""

echo "Python version:"
python --version

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