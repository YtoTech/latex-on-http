import subprocess

CURRENT_API_VERSION = None

def get_api_version():
    global CURRENT_API_VERSION
    if not CURRENT_API_VERSION:
        CURRENT_API_VERSION = subprocess.check_output(["git", "describe", "--always"]).strip().decode("utf-8")
    return CURRENT_API_VERSION
