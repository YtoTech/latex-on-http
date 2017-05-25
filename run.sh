export PYTHONIOENCODING=utf-8
virtualenv -p python3 venv/
venv/bin/pip3 install -r requirements.txt
venv/bin/python3 latex-on-http/app.py
