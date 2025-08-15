#!/usr/bin/env bash

# Silently deactivate any existing venv:
deactivate >/dev/null 2>&1
#deactivate

# Create venv environment if not present:

if [ ! -f ~/.venv/py-kubeview/bin/activate ]; then
    python3 -m venv ~/.venv/py-kubeview

fi

# Activate venv environment:
.  ~/.venv/py-kubeview/bin/activate

# Pip install necessary modules:

python3 -m pip install -U pip
python3 -m pip install reloadserver graphviz kubernetes

