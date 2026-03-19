@echo off

call pyenv local 3.10.11

pyenv exec python -m venv env

call env\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

pause