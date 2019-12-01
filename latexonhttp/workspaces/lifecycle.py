# -*- coding: utf-8 -*-
"""
    latexonhttp.workspaces.lifecycle
    ~~~~~~~~~~~~~~~~~~~~~
    Lifecycle management for build workspaces.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import uuid
from .filesystem import delete_workspace, make_workspace


def create_workspace(_resources):
    workspace_id = str(uuid.uuid4())
    make_workspace(workspace_id)
    return workspace_id


def remove_workspace(workspace_id):
    delete_workspace(workspace_id)
