@echo off
chcp 65001 >nul
echo Installing optional GLB preview dependencies...
python -m pip install --upgrade pillow matplotlib trimesh numpy
pause
