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
import codecs
import os
import shutil
import logging

logger = logging.getLogger(__name__)

# TODO Temporary dirty work.
# Lol.
# (Like any Python script that grow indefinitely?)


def run_command(directory, command):
    # TODO And if the command fails?
    # Currently it is stuck here!
    stdout = ""
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=directory
    )
    # Always have a timeout to control max compilation time and in case the
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


def latexToPdf(compilerName, directory, main_resource):
    if compilerName not in ["latex", "lualatex", "xelatex", "pdflatex"]:
        raise ValueError("Invalid compiler")
    # TODO Choose appropriate options following the compiler.
    # Copy files to tmp directory.
    # Should already be an absolute path (in our usage), but just to be sure.
    directory = os.path.abspath(directory)
    # TODO Uses workspace.filesystem module to these get paths.
    input_path = directory + "/{}".format(main_resource["build_path"])
    output_path = directory + "/output.pdf"
    log_dir = directory + "/latex.out"
    logger.info("Compiling %s from %s", main_resource["build_path"], directory)
    # print("Writing file")
    # print(input_path)
    # TODO Force UTF-8?
    # with open(inputPath, 'w') as f:
    #     f.write(latex)
    # TODO I don't know what I'm doing here.
    # with codecs.open(inputPath, "wb", "utf-8") as f:
    #     f.write(latex)
    # Use https://github.com/aclements/latexrun
    # to manage multiple runs of Latex compiler for us.
    # (Cross-references, page numbers, etc.)
    # TODO Put on pip
    # TODO Fix this lame subprocessing with parh orgy.
    command = [
        "python",
        os.getcwd() + "/latexonhttp/latexrun.py",
        "--latex-cmd=" + compilerName,
        "-O=" + log_dir,
        "-o=" + output_path,
        # Return all logs.
        "-W=all"
        # TODO Add -halt-on-error --interaction=nonstopmode
        '--latex-args="--output-format=pdf"',
        input_path,
    ]
    logger.debug(command)
    commandOutput = run_command(directory, command)
    # TODO Check for compilation errors.
    # commandOutput['return_code'] is not 0
    # Return both generated PDF and compile logs.
    pdf = None
    if os.path.isfile(output_path):
        with open(output_path, "rb") as f:
            pdf = f.read()
    # Clean things up before returning.
    shutil.rmtree(directory)
    return {"pdf": pdf, "logs": commandOutput["stdout"]}
