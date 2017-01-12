import subprocess
import codecs
import os

# TODO Temporary dirty work.

def run_command(command):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    while True:
        output = process.stdout.readline()
        if process.poll() is not None:
            break
        if output:
            # TODO Don't need output on the terminal.
            print(output.strip())
    rc = process.poll()
    # TODO Does it return command output?
    return rc

def latexToPdf(compilerName, directory, latex):
    if compilerName not in ['latex', 'lualatex', 'xelatex', 'pdflatex']:
        raise ValueError('Invalid compiler')
    # TODO Choose appropriate options following the compiler.
    # Copy files to tmp directory.
    # TODO Handle filesystem in another part. Check path.
    directory = os.path.abspath(directory)
    os.makedirs(directory)
    inputPath = directory + '/input.tex'
    outputPath = directory + '/input.pdf'
    print("Writing file")
    print(inputPath)
    # TODO Force UTF-8?
    # with open(inputPath, 'wb', 'utf-8') as f:
    with open(inputPath, 'wb') as f:
        f.write(latex)
    print('--output-directory=' + directory)
    print(inputPath)
    run_command([
        compilerName,
        '--output-format=pdf',
        '--output-directory=' + directory,
        inputPath]
    )
    # TODO Check for compilation errors.
    # TODO Return compile log.
    if (os.path.isfile(outputPath)):
        with open(outputPath, 'r') as f:
            return f.read()
    # TODO Clean things up before returning.
