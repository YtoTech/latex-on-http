"""
    tests.utils.pdf
    ~~~~~~~~~~~~~~~~~~~~~
    Helpers to snapshot and compare PDF files.

    :copyright: (c) 2018 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""

import os
import re
import difflib
import hexdump
import pprint
import subprocess
from pdf2image import convert_from_bytes
from PIL import Image
from PIL.ImageChops import difference

SAMPLE_DIR = os.getcwd() + "/tests/samples/"
REGEX_CLEAN_LIST_RE = [
    {
        "target": r"<< \/Producer.+>>",
        "replace_by": "<</Producer cleaned>>",
    },
    # {
    #     "target": r"<<\.\/Producer.+>>",
    #     "replace_by": "<</Producer cleaned>>",
    # },
    {
        "target": r"CreationDate \(D:[\d]+Z\)",
        "replace_by": "CreationDate cleaned",
    },
    {
        "target": r"ModDate \(D:[\d]+Z\)",
        "replace_by": "ModDate cleaned",
    },
    {
        "target": r"R \/ID \[ <\.+> ]",
        "replace_by": "R /ID [ <id1> <id2> ]",
    },
]

# We could also use diffpdf to compare PDFs:
# https://askubuntu.com/questions/40813/diff-of-two-pdf-files
# http://www.qtrac.eu/diffpdf.html


def clean_pdf_bytes_for_compare(data_bytes):
    for clean_re in REGEX_CLEAN_LIST_RE:
        data_bytes = re.sub(clean_re["target"], clean_re["replace_by"], data_bytes)
    return data_bytes


def pdf_compare_bytes(reference, compared, sample_dir):
    # Generated binary PDF files differs.
    # This line changes on each compilation, which is expected:
    # <</Producer (LuaTeX-1.07.0)/Creator (TeX)/CreationDate (D:20180701130853Z)/ModDate (D:20180701130853Z)/Trapped/False/PTEX.FullBanner (This is LuaTeX, Version 1.07.0 (TeX Live 2018))>>
    # <<./Producer (pdfTeX-1.40.26)./Creator (TeX)./CreationDate (D:20250213133648Z)./ModDate (D:20250213133648Z)./Trapped /False./PTEX.Fullbanner (This is pdfTeX, Version 3.141592653-2.6-1.40.26 (TeX Live 2024) kpathsea version 6.4.0).>>
    # We just strip it out for the moment.
    reference_cleaned = clean_pdf_bytes_for_compare(str(reference))
    compared_cleaned = clean_pdf_bytes_for_compare(str(compared))
    if compared_cleaned != reference_cleaned:
        sample_hex_path = "{}sample.hexdump".format(sample_dir)
        generated_hex_path = "{}generated.hexdump".format(sample_dir)
        hexdump_reference = hexdump.hexdump(reference, result="return")
        hexdump_generated = hexdump.hexdump(compared, result="return")
        with open(sample_hex_path, "w") as f:
            f.write(hexdump_reference)
        with open(generated_hex_path, "w") as f:
            f.write(hexdump_generated)
        sample_hex_cleaned_path = "{}sample.cleaned.hexdump".format(sample_dir)
        generated_hex_cleaned_path = "{}generated.cleaned.hexdump".format(sample_dir)
        hexdump_reference = hexdump.hexdump(str.encode(reference_cleaned), result="return")
        hexdump_generated = hexdump.hexdump(str.encode(compared_cleaned), result="return")
        with open(sample_hex_cleaned_path, "w") as f:
            f.write(hexdump_reference)
        with open(generated_hex_cleaned_path, "w") as f:
            f.write(hexdump_generated)
        # differ = difflib.Differ
        compared = list(
            difflib.context_diff(
                hexdump_reference,
                hexdump_generated,
                fromfile="sample.pdf",
                tofile="generated.pdf",
            )
        )
        diff_difflib_hex_path = "{}diff_difflib.hexdump".format(sample_dir)
        with open(diff_difflib_hex_path, "w") as f:
            for line in compared:
                f.write(line)
        diff_compared = subprocess.run(
            ["diff", sample_hex_path, generated_hex_path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).stdout
        pprint.pprint(diff_compared)
        diff_diff_hex_path = "{}diff_diff.hexdump".format(sample_dir)
        with open(diff_diff_hex_path, "wb") as f:
            f.write(diff_compared)
    assert compared_cleaned == reference_cleaned


def snapshot_pdf_bytes(pdf, sample_dir, update_snapshot):
    sample_pdf_path = "{}sample.pdf".format(sample_dir)
    generated_pdf_path = "{}generated.pdf".format(sample_dir)
    if update_snapshot:
        with open(sample_pdf_path, "wb") as f:
            f.write(pdf)
    with open(generated_pdf_path, "wb") as f:
        f.write(pdf)
    with open(sample_pdf_path, "rb") as f:
        sample_bytes = f.read()
        assert len(pdf) == len(sample_bytes)
        pdf_compare_bytes(sample_bytes, pdf, sample_dir)


def snapshot_pdf_text(pdf, sample_dir, update_snapshot):
    pass
    # TODO Use https://github.com/euske/pdfminer to extract and compare texts?
    # Seems overkill as we already compares bytes.


def snapshot_pdf_images(pdf, sample_dir, update_snapshot):
    # https://github.com/Belval/pdf2image
    # https://gist.github.com/santiago-kai/9a18ffabbc49bc2518c695cc140e0214
    sample_path_pattern = "{}sample_page_{}.jpg"
    generated_path_pattern = "{}generated_page_{}.jpg"
    images = convert_from_bytes(pdf)
    if update_snapshot:
        for i, image in enumerate(images):
            image.save(sample_path_pattern.format(sample_dir, i + 1))
    for i, image in enumerate(images):
        image.save(generated_path_pattern.format(sample_dir, i + 1))
        sample_image = Image.open(sample_path_pattern.format(sample_dir, i + 1))
        # Reopen to have consistent data bytes to bytes (depends of compression used when saving to file).
        generated_image = Image.open(generated_path_pattern.format(sample_dir, i + 1))
        # Make a more high-level diff.
        # See difference factors:
        # https://www.pyimagesearch.com/2014/09/15/python-compare-two-images/
        # Find diff sectos:
        # https://www.pyimagesearch.com/2017/06/19/image-difference-with-opencv-and-python/
        # https://docs.opencv.org/trunk/d7/d4d/tutorial_py_thresholding.html
        # assert sample_image.histogram() == generated_image.histogram()
        # assert sample_image.tobytes() == generated_image.tobytes()


def snapshot_pdf(pdf, sample, update_snapshot=False):
    sample_dir = "{}{}/".format(SAMPLE_DIR, sample)
    if update_snapshot and not os.path.exists(sample_dir):
        os.makedirs(sample_dir)
    snapshot_pdf_bytes(pdf, sample_dir, update_snapshot)
    snapshot_pdf_text(pdf, sample_dir, update_snapshot)
    # TODO Disabled as not reliable following the machine used to run tests.
    # snapshot_pdf_images(pdf, sample_dir, update_snapshot)
    # TODO If difference detected, output diff.
    # Neat library to visualize differences in PDFs.
    # https://github.com/JoshData/pdf-diff
