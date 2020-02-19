#!/bin/bash

# colors
RED='\033[0;31m'
NC='\033[0m'

GITDIR=$(git rev-parse --show-toplevel)
if [[ ! -d $GITDIR ]]; then
  read -p "Can't detect git directory (probably being run from outside the repo), where is the autopilot repository?: " GITDIR
fi




echo -e "${RED}Installing system dependencies\n${NC}"
if [[ "$OSTYPE" == "linux-gnu" ]]; then
  echo -e "${RED}Installing XLib g++ and opencv...\n${NC}"
  sudo apt-get update
  sudo apt-get install -y libxext-dev python-opencv g++
fi

echo -e "${RED}Installing Python dependencies\n${NC}"
sudo -H pip install -r "${GITDIR}/requirements_terminal.txt"
sudo -H pip install blosc



echo -e "${RED}Qt4 and PySide will be Compiled and installed...\n${NC}"



echo -e "${RED}Downloading & Compiling Qt4\n${NC}"

wget https://download.qt.io/archive/qt/4.8/4.8.7/qt-everywhere-opensource-src-4.8.7.zip

unzip -a ./qt-everywhere-opensource-src-4.8.7.zip

cd qt-everywhere-opensource-src-4.8.7

# make and install Qt4
./configure -confirm-license -debug -opensource -optimized-qmake -separate-debug-info -no-webkit -opengl
make -j10
sudo -H make install
cd ..

echo -e "${RED}Downloading & Compiling PySide\n${NC}"

git clone https://github.com/PySide/pyside-setup.git pyside-setup
cd pyside-setup
python setup.py bdist_wheel --standalone --qmake=$(which qmake)
sudo -H pip install dist/$(ls PySide*.whl)

# TODO: Add option to delete download filed






