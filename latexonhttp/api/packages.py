# -*- coding: utf-8 -*-
"""
    latexonhttp.api.packages
    ~~~~~~~~~~~~~~~~~~~~~
    Manage LaTeX-On-HTTP Latex packages.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
from flask import Blueprint, url_for
from texlivemetadata import list_installed_packages, get_package_info, get_ctan_link

packages_app = Blueprint("packages", __name__)

# TODO Add a cache.
# The tlmgr_packages calls take a lot of time.
# As the result should (must?) remains the same after
# an instance as been launched, we could cache each results
# (list and package info) in memory.


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
    return ({"packages": packages}, 200)


@packages_app.route("/<package_name>", methods=["GET"])
def packages_info(package_name):
    package_info = get_package_info(package_name)
    if not package_info:
        return ({"error": "Package not found"}, 404)
    package_info = {**package_info, "url_ctan": get_ctan_link(package_info["package"])}
    if "cat-date" in package_info:
        package_info["cat-date"] = (package_info["cat-date"].isoformat(),)
    return ({"package": package_info}, 200)
