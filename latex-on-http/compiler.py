import subprocess
import codecs
import os
import shutil

# TODO Temporary dirty work.

def run_command(command):
    # TODO And if the command fails?
    # Currently it is stuck herer!
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
    print("Compiling")
    # print(latex)
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
    # with open(inputPath, 'w') as f:
    #     f.write(latex)
    # TODO I don't know what I'm doing here.
    with codecs.open(inputPath, 'wb', 'utf-8') as f:
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
    pdf = None
    if (os.path.isfile(outputPath)):
        with open(outputPath, 'rb') as f:
            pdf = f.read()
        # Clean things up before returning.
        shutil.rmtree(directory)
    return pdf
