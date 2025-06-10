# Python Virtual Environment Setup

This project uses a Python 3.9 virtual environment for dependency management.

## Virtual Environment Details

- **Python Version**: 3.9.1
- **Location**: `./venv/`
- **Created with**: `/home/utils/Python-3.9.1/bin/python3.9`

## Quick Start

### Option 1: Use the activation script (Recommended)
```bash
source activate_venv.sh
```

### Option 2: Direct execution (No activation needed)
```bash
# Use Python from virtual environment
./venv/bin/python your_script.py

# Install packages
./venv/bin/pip install package_name

# Install from requirements.txt
./venv/bin/pip install -r requirements.txt
```

## Managing Dependencies

### Install packages
```bash
# After activation
pip install package_name

# Or directly
./venv/bin/pip install package_name
```

### Update requirements.txt
```bash
# After installing your packages
pip freeze > requirements.txt
```

### Install from requirements.txt
```bash
pip install -r requirements.txt
```

## Shell Compatibility

### For zsh/bash users (Current setup)
```bash
source activate_venv.sh
```

### For tcsh/csh users
If you're using tcsh, you can either:
1. Use direct execution: `./venv/bin/python script.py`
2. Or try the standard activation: `source venv/bin/activate.csh`

### Deactivation
```bash
# Unset environment and aliases
unset VIRTUAL_ENV
unalias python pip
export PATH=$(echo $PATH | sed 's|/home/scratch.louiliu_vlsi_1/sideProject/coverity-agent/venv/bin:||')

# Or simply start a new shell session
```

## Verification

Check if virtual environment is active:
```bash
python --version  # Should show Python 3.9.1
which python      # Should point to venv/bin/python
pip --version      # Should reference the venv directory
```

## Troubleshooting

### If activation fails
- Try direct execution: `./venv/bin/python`
- Check your shell: `echo $SHELL`
- Use the appropriate activation script for your shell

### If packages aren't found
- Ensure virtual environment is activated
- Check Python path: `which python`
- Verify installation: `pip list`

## Project Structure
```
coverity-agent/
├── venv/                 # Virtual environment
├── src/                  # Source code
├── requirements.txt      # Project dependencies
├── activate_venv.sh      # Activation script (bash/zsh)
├── activate_venv.csh     # Activation script (tcsh/csh)
└── VENV_SETUP.md        # This file
``` 