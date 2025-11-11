#!/bin/bash
# Simple script to activate or deactivate the virtual environment

VENV_DIR="venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$1" == "activate" ]]; then
    echo "🟢 Activating virtual environment..."
    source "$SCRIPT_DIR/$VENV_DIR/bin/activate"
    echo "✅ Virtual environment activated!"
    echo "   Python: $(which python)"
    echo "   To deactivate, run: deactivate"
    
elif [[ "$1" == "deactivate" ]]; then
    echo "🔴 Deactivating virtual environment..."
    deactivate 2>/dev/null || echo "⚠️  No virtual environment is currently active"
    
elif [[ "$1" == "status" ]]; then
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo "✅ Virtual environment is active"
        echo "   Location: $VIRTUAL_ENV"
        echo "   Python: $(which python)"
    else
        echo "⚠️  No virtual environment is currently active"
    fi
    
else
    echo "Usage: source $0 [activate|deactivate|status]"
    echo ""
    echo "Commands:"
    echo "  activate    - Activate the virtual environment"
    echo "  deactivate  - Deactivate the virtual environment"
    echo "  status      - Check if virtual environment is active"
    echo ""
    echo "Note: You must use 'source' to run this script:"
    echo "  source ./venv_control.sh activate"
fi
