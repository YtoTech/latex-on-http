from flask import Blueprint, jsonify, url_for
from latexonhttp.tlmgr_packages import (
    list_installed_packages,
    get_package_info,
    get_ctan_link,
)

packages_app = Blueprint("packages", __name__)


@packages_app.route("", methods=["GET"])
def packages_list():
    packages = [
        {
            **package,
            # TODO How to get a full link?
            "url_info": url_for(".packages_info", package_name=package["name"]),
            "url_ctan": get_ctan_link(package["name"]),
        }
        for package in list_installed_packages()
    ]
    return (jsonify({"packages": packages}), 200)


@packages_app.route("/<package_name>", methods=["GET"])
def packages_info(package_name):
    package_info = get_package_info(package_name)
    if not package_info:
        return (jsonify("Package not found"), 404)
    package_info = {
        **package_info,
        "cat-date": package_info["cat-date"].isoformat(),
        "url_ctan": get_ctan_link(package_info["package"]),
    }
    return (jsonify({"package": package_info}), 200)
