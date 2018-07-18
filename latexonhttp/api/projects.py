from flask import Blueprint, request

projects_app = Blueprint("projects", __name__)

# Projects management.


@projects_app.route("/", methods=["POST"])
def template_project_create():
    payload = request.get_json()
    # TODO Only for super-admin now.
    # TODO Open to registered users:
    # create user and service subscription management.
    # TODO Create template project with files.
