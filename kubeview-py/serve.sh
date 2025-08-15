
# To activate venv if invoking python directly:
# . ~/.venv/py-kubeview/bin/activate

cd $(dirname $0)/html

pwd

# Invoke reloadserver (http.server with auto page refresh):
~/.venv/py-kubeview/bin/python3 -m reloadserver

