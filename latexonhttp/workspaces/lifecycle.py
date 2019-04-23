import uuid
from .filesystem import delete_workspace


def create_workspace(_resources):
    return str(uuid.uuid4())


def remove_workspace(workspace_id):
    delete_workspace(workspace_id)
