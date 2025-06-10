#!/bin/tcsh
# Simple script to set up the Python virtual environment for coverity-agent
# Usage: source activate_venv.csh

setenv VIRTUAL_ENV "/home/scratch.louiliu_vlsi_1/sideProject/coverity-agent/venv"
setenv PATH "$VIRTUAL_ENV/bin:$PATH"

# Create aliases for convenience
alias python '$VIRTUAL_ENV/bin/python'
alias pip '$VIRTUAL_ENV/bin/pip'

echo "Virtual environment activated!"
echo "Python version: `$VIRTUAL_ENV/bin/python --version`"
echo "To deactivate, simply restart your shell or unsetenv VIRTUAL_ENV" 