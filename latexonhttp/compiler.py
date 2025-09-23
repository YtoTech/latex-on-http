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
import glob
import glom
from latexonhttp.utils.processes import kill_all_children_processes

logger = logging.getLogger(__name__)
# In seconds.
DEFAULT_COMPILE_TIMEOUT = int(os.getenv("DEFAULT_COMPILE_TIMEOUT", 100))

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


def run_command(directory, command, timeout=DEFAULT_COMPILE_TIMEOUT):
    # TODO Security: add isolation mechanism.
    # - firejail? (https://firejail.wordpress.com/)
    # - Docker? (like https://github.com/overleaf/clsi)
    # TODO Limit resource use by a given compilation job?
    # Managed through Docker container, but we could add fine grained limits
    # here too?
    # https://unix.stackexchange.com/questions/151883/limiting-processes-to-not-exceed-more-than-10-of-cpu-usage
    stdout = ""
    is_timeout = False
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=directory,
        universal_newlines=True,
    )
    started_at = timeit.default_timer()
    # Always have a timeout to control max compilation time and in case the
    # process is stuck.
    while True:
        try:
            polled_at = timeit.default_timer()
            out, err = process.communicate(timeout=0.2)
            if out:
                stdout += str(out)
                # logger.debug(out.strip())
        except subprocess.TimeoutExpired:
            pass
        if process.poll() is not None:
            break
        if (polled_at - started_at) > timeout:
            logger.warning("Process timeout, killing it")
            # Kill the whole process group.
            kill_all_children_processes(process.pid)
            is_timeout = True
            stdout += "Compilation timeout, process killed\n"
            break
    try:
        out, err = process.communicate(timeout=2)
        if out:
            stdout += str(out)
            # logger.debug(out.strip())
    except subprocess.TimeoutExpired:
        pass
    rc = process.wait()
    ended_at = timeit.default_timer()
    logger.debug("Program returned with status code %d", rc)
    return {
        "return_code": rc,
        "stdout": stdout,
        "duration": ended_at - started_at,
        "is_timeout": is_timeout,
    }


def latexToPdf(compilerName, directory, main_resource, workspace_id, options={}):
    bibtexCommand = glom.glom(options, "bibliography.command", default="bibtex")
    if bibtexCommand not in AVAILABLE_BIBLIOGRAPHY_COMMANDS:
        raise ValueError("Invalid bibtex command")
    if compilerName not in AVAILABLE_LATEX_COMPILERS:
        raise ValueError("Invalid compiler")
    # TODO Choose appropriate options following the compiler.
    # Copy files to tmp directory.
    # Should already be an absolute path (in our usage), but just to be sure.
    directory = os.path.abspath(directory)
    input_path = os.path.join(directory, main_resource["build_path"])
    output_path = os.path.join(
        directory, main_resource["build_path"].replace(".tex", ".pdf")
    )
    logger.info("Compiling %s from %s", main_resource["build_path"], directory)
    if compilerName in ["context"]:
        # Here do not support multi runs or bibtex/biber commands.
        # --> do not pass nonstopmode
        # --> parse jobName / output files from Context output
        # Alternative: support many runners.
        # Arara https://github.com/cereda/arara
        # https://github.com/wtsnjp/llmk
        command = [
            compilerName,
            input_path,
        ]
    else:
        # Use https://mgeier.github.io/latexmk.html
        # to manage multiple runs of Latex compiler for us.
        # (Cross-references, page numbers, etc.)
        # Create the .latexmkrc configuration file.
        # We enable -synctex=1 (only useful if we
        # return the whole directory).
        # TODO Let the config be provided? (dangerous)
        #  -> After the process is hardened.
        mainLatexCmd = "latex" if compilerName in ["platex", "uplatex"] else "pdflatex"
        # TODO Option to use -shell-escape ft. -no-shell-escape
        #  -> Only in premium / connected mode.
        # Option to use -halt-on-error to stop on first error.
        halt_on_error = glom.glom(options, "compiler.halt_on_error", default=False)
        silent = glom.glom(options, "compiler.silent", default=False)
        interaction_mode = "batchmode" if silent else "nonstopmode"
        halt_on_error_str = " -halt-on-error" if halt_on_error else ""
        latexmkrc = f"""${mainLatexCmd} = '{compilerName} -interaction={interaction_mode}{halt_on_error_str} -file-line-error -synctex=1 %O %S';
"""
        logger.debug(".latexmkrc: %s", latexmkrc)
        with open(os.path.join(directory, ".latexmkrc"), "w") as fd:
            fd.write(latexmkrc)
        # As an option, use -silent (aka -interaction=batchmode)
        command = [
            "latexmk",
            "-pdfps" if compilerName in ["platex", "uplatex"] else "-pdf",
        ]
        command += ["-silent"] if silent else []
        command += [main_resource["build_path"]]
    logger.debug(command)
    mainCmdOutput = run_command(directory, command)
    commandOutputs = [mainCmdOutput]
    # if commandOutputs[0]["return_code"] == 0 and compilerName in ["platex", "uplatex"]:
    #     # We need a dvipdfmx pass.
    #     # https://tex.stackexchange.com/questions/295414/what-is-uptex-uplatex
    #     # TODO Use ptex2pdf?
    #     # https://github.com/texjporg/ptex2pdf
    #     command = [
    #         "dvipdfmx",
    #         "{}/{}".format(
    #             log_dir, main_resource["build_path"].replace(".tex", ".dvi")
    #         ),
    #     ]
    #     output_path = "{}/{}".format(
    #         log_dir, main_resource["build_path"].replace(".tex", ".pdf")
    #     )
    #     logger.debug(command)
    #     commandOutputs.append(run_command(log_dir, command))
    # Return both generated PDF and compile logs.
    # TODO Uses workspace.filesystem module read file back?
    pdf = None
    commandsStatusCodes = [
        commandOutput["return_code"] for commandOutput in commandOutputs
    ]
    # We do not check status codes, they are not reliable with Latexmk.
    # all(
    #     commandOutput["return_code"] in [0] for commandOutput in commandOutputs
    # )
    logger.info(output_path)
    if os.path.isfile(output_path):
        with open(output_path, "rb") as f:
            pdf = f.read()
    is_timeout = any(commandOutput["is_timeout"] for commandOutput in commandOutputs)
    status = "ok" if pdf and not is_timeout else "ko"
    logger.info("Compilation %s is %s: %s", workspace_id, status, commandsStatusCodes)
    log_files = {}
    # Get the log files.
    for log_path in glob.glob("*.log", root_dir=directory):
        with open(os.path.join(directory, log_path), "r") as f:
            log_files[log_path] = f.read()
    return {
        # TODO Also return each command metadatas for db.
        "status": status,
        "pdf": pdf,
        "log_files": log_files,
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
        "is_timeout": is_timeout,
    }
