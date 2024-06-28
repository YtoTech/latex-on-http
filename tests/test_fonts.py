"""
    tests.test_fonts
    ~~~~~~~~~~~~~~~~~~~~~
    Test fonts API.

    :copyright: (c) 2018 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""

import requests


def test_api_fonts_list(latex_on_http_api_url):
    """
    The API list available fonts.
    """
    r = requests.get("{}/fonts".format(latex_on_http_api_url), allow_redirects=False)
    assert r.status_code == 200
    payload = r.json()
    assert "fonts" in payload
    fonts = payload["fonts"]
    assert isinstance(fonts, list) is True
    for font in fonts:
        assert "family" in font
        assert "name" in font
        assert "styles" in font
        assert isinstance(font["styles"], list) is True
    assert len(fonts) > 2600
    assert len(fonts) < 2900
