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
import stat
import timeit
import logging
import glob
import glom
from latexonhttp.sandbox import (
    SandboxUnavailable,
    build_sandbox_command,
    prepare_workspace,
    sandbox_enabled,
)
from latexonhttp.utils.processes import (
    kill_all_children_processes,
    terminate_process_group,
)

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


def run_command(
    directory,
    command,
    timeout=DEFAULT_COMPILE_TIMEOUT,
    shell_escape=False,
    isolate=None,
):
    """Run one complete command tree, isolated by default.

    Bubblewrap wraps latexmk itself rather than individual TeX passes, so all
    helper processes inherit its mounts, namespace and scrubbed environment.
    An explicit isolate=False is intended only for trusted local tests/tools.
    """
    original_command = command
    is_sandboxed = sandbox_enabled(isolate)
    if is_sandboxed:
        prepare_workspace(directory)
        command = build_sandbox_command(directory, command, shell_escape=shell_escape)
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=directory,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
    except FileNotFoundError as error:
        if is_sandboxed:
            raise SandboxUnavailable("Cannot start Bubblewrap") from error
        raise
    started_at = timeit.default_timer()
    is_timeout = False
    stdout = ""
    try:
        out, _ = process.communicate(timeout=timeout)
        stdout = out or ""
    except subprocess.TimeoutExpired:
        logger.warning("Process timeout, terminating its process group")
        is_timeout = True
        terminate_process_group(process.pid)
        try:
            out, _ = process.communicate(timeout=2)
            stdout = out or ""
        except subprocess.TimeoutExpired:
            kill_all_children_processes(process.pid)
            out, _ = process.communicate()
            stdout = out or ""
        stdout += "Compilation timeout, process group killed\n"
    rc = process.wait()
    if is_sandboxed and rc != 0 and stdout.lstrip().startswith("bwrap:"):
        raise SandboxUnavailable(stdout.strip())
    ended_at = timeit.default_timer()
    logger.debug("Program returned with status code %d", rc)
    return {
        "command": original_command,
        "return_code": rc,
        "stdout": stdout,
        "duration": ended_at - started_at,
        "is_timeout": is_timeout,
    }


MAX_PDF_SIZE = int(os.getenv("MAX_PDF_SIZE", 100 * 1024 * 1024))
MAX_LOG_FILE_SIZE = int(os.getenv("MAX_LOG_FILE_SIZE", 10 * 1024 * 1024))


def _read_generated_file(path, max_size):
    """Read a regular output without following compiler-created symlinks."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_descriptor = os.open(path, flags)
        with os.fdopen(file_descriptor, "rb") as fd:
            if not stat.S_ISREG(os.fstat(fd.fileno()).st_mode):
                logger.warning("Ignoring non-regular compilation output %s", path)
                return None
            data = fd.read(max_size + 1)
            if len(data) > max_size:
                logger.warning("Ignoring oversized compilation output %s", path)
                return None
            return data
    except OSError as error:
        # This includes missing files and ELOOP for symbolic links.
        logger.warning("Cannot safely read compilation output %s: %s", path, error)
        return None


def latexToPdf(compilerName, directory, main_resource, workspace_id, options={}):
    if compilerName not in AVAILABLE_LATEX_COMPILERS:
        raise ValueError("Invalid compiler")
    # TODO Choose appropriate options following the compiler.
    # Copy files to tmp directory.
    # Should already be an absolute path (in our usage), but just to be sure.
    directory = os.path.abspath(directory)
    output_path = os.path.join(
        directory, main_resource["build_path"].replace(".tex", ".pdf")
    )
    logger.info("Compiling %s from %s", main_resource["build_path"], directory)
    force_latexmk = glom.glom(options, "compiler.force", default=True)
    shell_escape = glom.glom(options, "compiler.shell_escape", default=False)
    if compilerName in ["context"]:
        # Here do not support multi runs or bibtex/biber commands.
        # --> do not pass nonstopmode
        # --> parse jobName / output files from Context output
        # Alternative: support many runners.
        # Arara https://github.com/cereda/arara
        # https://github.com/wtsnjp/llmk
        command = [
            compilerName,
            main_resource["build_path"],
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
        # Shell escape is always explicit. Enabling it adds only the curated
        # shell, Python and pygmentize commands to the already offline sandbox.
        shell_escape_option = "-shell-escape" if shell_escape else "-no-shell-escape"
        # Option to use -halt-on-error to stop on first error.
        halt_on_error = glom.glom(options, "compiler.halt_on_error", default=False)
        bibtex_latexmk = glom.glom(options, "compiler.bibliography", default=False)
        silent = glom.glom(options, "compiler.silent", default=False)
        interaction_mode = "batchmode" if silent else "nonstopmode"
        halt_on_error_str = " -halt-on-error" if halt_on_error else ""
        latexmkrc = f"""${mainLatexCmd} = '{compilerName} {shell_escape_option} -interaction={interaction_mode}{halt_on_error_str} -file-line-error -synctex=1 %O %S';
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
        command += ["-bibtex"] if bibtex_latexmk else []
        command += ["-f"] if force_latexmk else []
        command += [main_resource["build_path"]]
    logger.debug(command)
    mainCmdOutput = run_command(directory, command, shell_escape=shell_escape)
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
    pdf = _read_generated_file(output_path, MAX_PDF_SIZE)
    commandsStatusCodes = [
        commandOutput["return_code"] for commandOutput in commandOutputs
    ]
    # We do not check status codes, they are not reliable with Latexmk.
    # all(
    #     commandOutput["return_code"] in [0] for commandOutput in commandOutputs
    # )
    logger.info(output_path)
    is_timeout = any(commandOutput["is_timeout"] for commandOutput in commandOutputs)
    status = None
    if force_latexmk:
        status = "ok" if pdf and not is_timeout else "ko"
    else:
        status = (
            "ok"
            if all(
                commandOutput["return_code"] in [0] for commandOutput in commandOutputs
            )
            and pdf
            else "ko"
        )
    logger.info("Compilation %s is %s: %s", workspace_id, status, commandsStatusCodes)
    log_files = {}
    # Get the log files.
    for log_path in glob.glob("*.log", root_dir=directory):
        log_data = _read_generated_file(
            os.path.join(directory, log_path), MAX_LOG_FILE_SIZE
        )
        if log_data is not None:
            log_files[log_path] = log_data.decode("utf-8", errors="replace")
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
        "commands": commandOutputs,
        "is_timeout": is_timeout,
    }
