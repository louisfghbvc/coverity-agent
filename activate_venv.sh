#!/bin/bash
# Virtual environment activation script for coverity-agent
# Usage: source activate_venv.sh

export VIRTUAL_ENV="/home/scratch.louiliu_vlsi_1/sideProject/coverity-agent/venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"

# Create aliases for convenience
alias python='$VIRTUAL_ENV/bin/python'
alias pip='$VIRTUAL_ENV/bin/pip'

echo "Virtual environment activated!"
echo "Python version: $($VIRTUAL_ENV/bin/python --version)"
echo "To deactivate: unset VIRTUAL_ENV; unalias python pip; export PATH=\$(echo \$PATH | sed 's|$VIRTUAL_ENV/bin:||')" 