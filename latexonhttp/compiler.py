# -*- coding: utf-8 -*-
"""
    latexonhttp.compiler
    ~~~~~~~~~~~~~~~~~~~~~
    The Latex compiler abstraction.
    Get a compilation order (dict task spec) and compiles the order.

    :copyright: (c) 2017-2018 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import subprocess
import os
import logging
import glom

logger = logging.getLogger(__name__)

# TODO Temporary dirty work.
# Lol.
# (Like any Python script that grow indefinitely?)

# TODO Let users access tex, latex, dvilualatex, ptex and uptexfor DVI output.
# https://tex.stackexchange.com/a/397312/122145
# TODO Support also pandoc?
AVAILABLE_LATEX_COMPILERS = [
    "pdflatex",
    "xelatex",
    "lualatex",
    "platex",
    "uplatex",
    "context",
]
AVAILABLE_BIBLIOGRAPHY_COMMANDS = ["bibtex", "biber"]


def run_command(directory, command):
    # TODO Security: add isolation mechanism.
    # - firejail? (https://firejail.wordpress.com/)
    # - Docker? (like https://github.com/overleaf/clsi)
    # TODO And if the command fails?
    # Currently it is stuck here!
    stdout = ""
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=directory
    )
    # TODO Always have a timeout to control max compilation time and in case the
    # process is stuck.
    # try:
    #     out, err = process.communicate(timeout=15)
    #     print(out)
    # except subprocess.TimeoutExpired:
    #     process.kill()
    #     out, err = process.communicate()
    #     print(out)
    # TODO Read output line by line in a thread (so we have a timeout if external process stucks?)
    while True:
        output = process.stdout.readline()
        if process.poll() is not None:
            break
        if output:
            # TODO Don't need output on the terminal.
            stdout += str(output) + "\n"
            print(output.strip())
    rc = process.poll()
    logger.debug("Program returned with status code %d", rc)
    # TODO Does it return command output?
    return {"return_code": rc, "stdout": stdout}


def latexToPdf(compilerName, directory, main_resource, options={}):
    bibtexCommand = glom.glom(options, "bibliography.command", default="bibtex")
    if bibtexCommand not in AVAILABLE_BIBLIOGRAPHY_COMMANDS:
        raise ValueError("Invalid bibtex command")
    if compilerName not in AVAILABLE_LATEX_COMPILERS:
        raise ValueError("Invalid compiler")
    # TODO Choose appropriate options following the compiler.
    # Copy files to tmp directory.
    # Should already be an absolute path (in our usage), but just to be sure.
    directory = os.path.abspath(directory)
    # TODO Uses workspace.filesystem module to these get paths.
    input_path = "{}/{}".format(directory, main_resource["build_path"])
    output_path = "{}/output.pdf".format(directory)
    log_dir = "{}/latex.out".format(directory)
    logger.info("Compiling %s from %s", main_resource["build_path"], directory)
    # Use https://github.com/aclements/latexrun
    # to manage multiple runs of Latex compiler for us.
    # (Cross-references, page numbers, etc.)
    # TODO Put on pip
    # TODO Fix this lame subprocessing with parh orgy.
    if compilerName in ["context"]:
        # TODO Patch latexrun to support context?
        # Here do not support multi runs or bibtex/biber commands.
        # --> do not pass nonstopmode
        # --> parse jobName / output files from Context output
        # Or use another more universal Latex runner?
        # https://mg.readthedocs.io/latexmk.html
        command = [
            compilerName,
            input_path,
        ]
        output_path = "{}/{}".format(
            directory, main_resource["build_path"].replace(".tex", ".pdf")
        )
        log_dir = "{}/{}".format(
            directory, main_resource["build_path"].replace(".tex", ".log")
        )
    else:
        command = [
            "python",
            "{}/latexonhttp/latexrun.py".format(os.getcwd()),
            "--latex-cmd={}".format(compilerName),
            "-O={}".format(log_dir),
            "-o={}".format(output_path),
            # Return all logs.
            "-W=all"
            # TODO Add -halt-on-error --interaction=nonstopmode
            # TODO Let user choose DVI (or other supported) output.
            '--latex-args="--output-format=pdf"',
            "--bibtex-cmd={}".format(bibtexCommand),
            input_path,
        ]
    logger.debug(command)
    commandOutput = run_command(directory, command)
    if commandOutput["return_code"] == 0 and compilerName in ["platex", "uplatex"]:
        # We need a dvipdfmx pass.
        # https://tex.stackexchange.com/questions/295414/what-is-uptex-uplatex
        # TODO Use ptex2pdf?
        # https://github.com/texjporg/ptex2pdf
        command = [
            "dvipdfmx",
            "{}/{}".format(
                log_dir, main_resource["build_path"].replace(".tex", ".dvi")
            ),
        ]
        output_path = "{}/{}".format(
            log_dir, main_resource["build_path"].replace(".tex", ".pdf")
        )
        logger.debug(command)
        run_command(log_dir, command)
    # TODO Check for compilation errors.
    # commandOutput['return_code'] is not 0
    # Return both generated PDF and compile logs.
    # TODO Uses workspace.filesystem module read file back?
    pdf = None
    if os.path.isfile(output_path):
        with open(output_path, "rb") as f:
            pdf = f.read()
    # TODO Returns paths instead of data?
    return {
        "pdf": pdf,
        "output_path": main_resource["output_path"],
        "logs": commandOutput["stdout"],
    }
