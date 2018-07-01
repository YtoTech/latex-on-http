import os
import re
# from pdf2image import convert_from_bytes

SAMPLE_DIR = os.getcwd() + "/tests/samples/"
REGEX_CLEAN = r"<</Producer.+>>"

def clean_pdf_bytes_for_compare(bytes):
    return re.sub(REGEX_CLEAN, '<</Producer cleaned>>', bytes)

def pdf_compare_bytes(reference, compared):
    # Generated binary PDF files differs.
    # This line changes on each compilation, which is expected:
    # <</Producer (LuaTeX-1.07.0)/Creator (TeX)/CreationDate (D:20180701130853Z)/ModDate (D:20180701130853Z)/Trapped/False/PTEX.FullBanner (This is LuaTeX, Version 1.07.0 (TeX Live 2018))>>
    # We just strip it out for the moment.
    reference_cleaned = clean_pdf_bytes_for_compare(str(reference))
    compared_cleaned = clean_pdf_bytes_for_compare(str(compared))
    assert compared_cleaned == reference_cleaned

def snapshot_pdf_bytes(pdf, sample_dir, update_snapshot):
    sample_pdf_path = "{}sample.pdf".format(sample_dir)
    generated_pdf_path = "{}generated.pdf".format(sample_dir)
    if update_snapshot:
        with open(sample_pdf_path, 'wb') as f:
            f.write(pdf)
    with open(generated_pdf_path, "wb") as f:
        f.write(pdf)
    with open(sample_pdf_path, "rb") as f:
        sample_bytes = f.read()
        assert len(pdf) == len(sample_bytes)
        pdf_compare_bytes(sample_bytes, pdf)

def snapshot_pdf_text(pdf, sample_dir, update_snapshot):
    pass
    # TODO Use https://github.com/euske/pdfminer to compare?

def snapshot_pdf_images(pdf, sample_dir, update_snapshot):
    # https://github.com/Belval/pdf2image
    # https://gist.github.com/santiago-kai/9a18ffabbc49bc2518c695cc140e0214
    pass

def snapshot_pdf(pdf, sample, update_snapshot=False):
    sample_dir = "{}{}/".format(SAMPLE_DIR, sample)
    snapshot_pdf_bytes(pdf, sample_dir, update_snapshot)
    snapshot_pdf_text(pdf, sample_dir, update_snapshot)
    snapshot_pdf_images(pdf, sample_dir, update_snapshot)
