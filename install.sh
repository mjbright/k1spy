#!/bin/bash
#
# Requires sudo privileges in order to work.
#
# Use the flag '--apt-get' to install python dependencies with apt-get 
# rather than apt - recommended for automation

install_dir=/usr/local/bin/k1s
get=0

while test $# -gt 0; do
    case "$1" in
        --apt-get)
            shift
            shift
            get=1
            ;;
        *)
            echo "$1 is not a recognized option."
            exit 1;
            ;;
    esac
done  

echo "Installing Python requirements..."
if [ $get -eq 0 ]
then
    sudo apt -qq update && sudo apt -qq install python3 python3-pip -y
else
    sudo apt-get -qq update && sudo apt-get -qq install python3 python3-pip -y
fi

echo
echo "Installing pip requirements..."
pip3 install -q kubernetes

sudo cp k1s.py $install_dir

echo
echo "k1s successfully installed in $install_dir."