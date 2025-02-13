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
import timeit
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


def run_command(directory, command, timeout=100):
    # TODO Security: add isolation mechanism.
    # - firejail? (https://firejail.wordpress.com/)
    # - Docker? (like https://github.com/overleaf/clsi)
    # TODO Limit resource use by a given compilation job.
    # https://tug.org/TUGboat/tb31-2/tb98doob.pdf
    # https://unix.stackexchange.com/questions/151883/limiting-processes-to-not-exceed-more-than-10-of-cpu-usage
    # https://scoutapm.com/blog/restricting-process-cpu-usage-using-nice-cpulimit-and-cgroups
    # https://unix.stackexchange.com/questions/44985/limit-memory-usage-for-a-single-linux-process
    # TODO And if the command fails?
    # Currently it is stuck here!
    stdout = ""
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=directory
    )
    started_at = timeit.default_timer()
    # TODO Always have a timeout to control max compilation time and in case the
    # process is stuck.
    # try:
    #     out, err = process.communicate(timeout=15)
    #     print(out)
    # except subprocess.TimeoutExpired:
    #     process.kill()
    #     out, err = process.communicate()
    #     print(out)
    while True:
        stdout_line = process.stdout.readline()
        if process.poll() is not None:
            break
        polled_at = timeit.default_timer()
        if stdout_line:
            stdout += str(stdout_line) + "\n"
            logger.debug(stdout_line.strip())
        if (polled_at - started_at) > timeout:
            logger.warning("Process timeout, killing it")
            process.kill()
            break
    rc = process.poll()
    ended_at = timeit.default_timer()
    logger.debug("Program returned with status code %d", rc)
    return {
        "return_code": rc,
        "stdout": stdout,
        "duration": ended_at - started_at,
    }


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
    # Use the same root directory to prevent issues
    # with filecontents and uploaded resources (path resolution).
    log_dir = "{}".format(directory)
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
        # Alternative: support many runners.
        # Arara https://github.com/cereda/arara
        # https://github.com/wtsnjp/llmk
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
            # TODO -shell-restricted / -shell-escape
            '--latex-args="--output-format=pdf"',
            "--bibtex-cmd={}".format(bibtexCommand),
            # "--debug",
            input_path,
        ]
    logger.debug(command)
    commandOutputs = [run_command(directory, command)]
    if commandOutputs[0]["return_code"] == 0 and compilerName in ["platex", "uplatex"]:
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
        commandOutputs.append(run_command(log_dir, command))
    # TODO Check for compilation errors.
    # commandOutputs[0]['return_code'] is not 0
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
        "duration": sum(commandOutput["duration"] for commandOutput in commandOutputs),
        # TODO New endpoints for new API with structure compile steps.
        "logs": "\n".join(
            [
                # TODO Display command header.
                commandOutput["stdout"]
                for commandOutput in commandOutputs
            ]
        ),
    }
