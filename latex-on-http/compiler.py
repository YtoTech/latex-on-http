# -*- coding: utf-8 -*-
import subprocess
import codecs
import os
import shutil

# TODO Temporary dirty work.

def run_command(directory, command):
    # TODO And if the command fails?
    # Currently it is stuck here!
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=directory
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
    # TODO Read output line by line in a thread
    while True:
        output = process.stdout.readline()
        if process.poll() is not None:
            break
        if output:
            # TODO Don't need output on the terminal.
            print(output.strip())
    rc = process.poll()
    print('Program returned with status code {}'.format(rc))
    # TODO Does it return command output?
    return rc

def latexToPdf(compilerName, directory, latex):
    if compilerName not in ['latex', 'lualatex', 'xelatex', 'pdflatex']:
        raise ValueError('Invalid compiler')
    print("Compiling")
    # print(latex)
    # TODO Choose appropriate options following the compiler.
    # Copy files to tmp directory.
    # TODO Handle filesystem in another part. Check path.
    directory = os.path.abspath(directory)
    os.makedirs(directory, exist_ok=True)
    inputPath = directory + '/input.tex'
    outputPath = directory + '/input.pdf'
    logDir = directory + '/latex.out'
    print("Writing file")
    print(inputPath)
    # TODO Force UTF-8?
    # with open(inputPath, 'w') as f:
    #     f.write(latex)
    # TODO I don't know what I'm doing here.
    with codecs.open(inputPath, 'wb', 'utf-8') as f:
        f.write(latex)
    # TODO We need to use something like https://github.com/aclements/latexrun
    # to manage multiple runs of Latex compiler for us.
    # (Cross-references, page numbers, etc.)
    command = [
        os.getcwd() + '/venv/bin/python3',
        os.getcwd() + '/latex-on-http/latexrun.py',
        '--latex-cmd=' + compilerName,
        '-O=' + logDir,
        '-o=' + outputPath,
        # TODO Add -halt-on-error
        '--latex-args="--output-format=pdf  --interaction=nonstopmode"',
        inputPath
    ]
    print(command)
    run_command(directory, command)
    # TODO Check for compilation errors.
    # TODO Return compile logs.
    pdf = None
    if (os.path.isfile(outputPath)):
        with open(outputPath, 'rb') as f:
            pdf = f.read()
    # Clean things up before returning.
    shutil.rmtree(directory)
    return pdf
