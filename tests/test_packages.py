"""
    tests.test_packages
    ~~~~~~~~~~~~~~~~~~~~~
    Test packages API.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""

import requests


def test_api_packages_list(latex_on_http_api_url):
    """
    The API list available/installed Texlive/tlgmr packages.
    """
    r = requests.get("{}/packages".format(latex_on_http_api_url), allow_redirects=False)
    assert r.status_code == 200
    payload = r.json()
    assert "packages" in payload
    packages = payload["packages"]
    assert isinstance(packages, list) is True
    for package in packages:
        assert "name" in package
        assert "shortdesc" in package
        assert "url_info" in package
        assert "url_ctan" in package
        assert "installed" in package
        assert package["installed"] is True
    # We use an interval, because number of packages
    # can changes between TexLive updates / releases.
    # (And the exact number is not so important,
    # when the full scheme is installed)
    assert len(packages) > 4000
    assert len(packages) < 5000


PACKAGE_INFO_MANDATORIES_PROPERTIES = [
    "package",
    "cat-license",
    "cat-topics",
    "cat-version",
    "category",
    "collection",
    "installed",
    "longdesc",
    "relocatable",
    "revision",
    "shortdesc",
    "sizes",
    "url_ctan",
]
PACKAGE_INFO_OPTIONAL_PROPERTIES = ["cat-contact-repository", "cat-related"]


def check_info_properties(package):
    for property_name in PACKAGE_INFO_MANDATORIES_PROPERTIES:
        assert property_name in package
    for key in package.keys():
        assert (
            key in PACKAGE_INFO_MANDATORIES_PROPERTIES
            or key in PACKAGE_INFO_OPTIONAL_PROPERTIES
        )


def test_api_packages_info_installed_xmltex(latex_on_http_api_url):
    """
    The API allow to get info on an installed package.
    """
    r = requests.get(
        "{}/packages/xmltex".format(latex_on_http_api_url), allow_redirects=False
    )
    assert r.status_code == 200
    payload = r.json()
    assert "package" in payload
    package = payload["package"]
    assert isinstance(package, dict) is True
    check_info_properties(package)
    assert isinstance(package["relocatable"], bool) is True
    assert isinstance(package["installed"], bool) is True
    assert isinstance(package["sizes"], dict) is True
    assert isinstance(package["cat-topics"], list) is True
    assert package["package"] == "xmltex"
    assert package["installed"] is True


def test_api_packages_info_installed_xpiano(latex_on_http_api_url):
    """
    The API allow to get info on an installed package.
    """
    r = requests.get(
        "{}/packages/xpiano".format(latex_on_http_api_url), allow_redirects=False
    )
    assert r.status_code == 200
    payload = r.json()
    assert "package" in payload
    package = payload["package"]
    assert isinstance(package, dict) is True
    check_info_properties(package)
    assert isinstance(package["relocatable"], bool) is True
    assert isinstance(package["installed"], bool) is True
    assert isinstance(package["sizes"], dict) is True
    assert isinstance(package["cat-topics"], list) is True
    assert package["package"] == "xpiano"
    assert package["installed"] is True


# def test_api_packages_info_not_installed(latex_on_http_api_url):
#     """
#     The API allow to get info on an not installed package.
#     """
#     r = requests.get(
#         "{}/packages/texworks.win32".format(latex_on_http_api_url),
#         allow_redirects=False,
#     )
#     assert r.status_code == 200
#     payload = r.json()
#     assert "package" in payload
#     package = payload["package"]
#     assert isinstance(package, dict) is True
#     assert "category" in package
#     assert "shortdesc" in package
#     assert "url_ctan" in package
#     assert isinstance(package["relocatable"], bool) is True
#     assert isinstance(package["installed"], bool) is True
#     assert isinstance(package["sizes"], dict) is True
#     assert package["package"] == "texworks.win32"
#     assert package["installed"] is False
