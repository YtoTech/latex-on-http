from flask import Flask, request, jsonify, redirect, Response
import compiler
import uuid
app = Flask(__name__)

# xelatex -output-directory /root/latex/ /root/latex/sample.tex

@app.route('/')
def hello():
    # TODO Distribute documentation. (HTML)
    return redirect("https://github.com/YtoTech/latex-on-http", code=302)

# TODO Only register request here, and allows to define an hook for when
# the work is done?
# Allows the two? (async, sync)
@app.route('/compilers/latex', methods=['POST'])
def compiler_latex():
    # TODO Distribute documentation. (HTML)
    payload = request.get_json()
    if not payload:
        return jsonify('MISSING_PAYLOAD'), 400
    # Choose compiler: latex, pdflatex, xelatex or lualatex
    # We default to lualatex.
    compilerName = 'lualatex'
    # TODO Choose them directly from the method?
    if 'compiler' in payload:
        if payload['compiler'] not in ['latex', 'lualatex', 'xelatex', 'pdflatex']:
            return jsonify('INVALID_COMPILER'), 400
        compilerName = payload['compiler']
    if not 'resources' in payload:
        return jsonify('MISSING_RESOURCES'), 400
    # TODO Must be an array.
    # Iterate on resources.
    mainResource = None
    for resource in payload['resources']:
        # Must have:
        # TODO Either data or url.
        # TODO Path relative to the project.
        if 'main' in resource and resource['main'] is True:
            mainResource = resource
        if 'url' in resource:
            # TODO Fetch and put in resource content.
            return jsonify('NOT_IMPLEMENTED'), 500
        if not 'content' in resource:
            return jsonify('MISSING_CONTENT'), 400
    # TODO If more than one resource, must give an main file flag.
    if len(payload['resources']) == 1:
        mainResource = payload['resources'][0]
    else:
        if not mainResource:
            return jsonify('MUST_SPECIFY_MAIN_RESOURCE'), 400
    if len(payload['resources']) > 1:
        return jsonify('NOT_IMPLEMENTED'), 500
    # We assume an unique Latex resource.
    # TODO Try catch.
    pdf = compiler.latexToPdf(
        compilerName,
        # TODO Absolute directory.
        './tmp/' + str(uuid.uuid4()),
        mainResource['content']
    )
    if not pdf:
        return jsonify('API_ERROR'), 500
    # TODO Specify ouput file name.
    return Response(
        pdf,
        status='201',
        headers={
            'Content-Type': 'application/pdf'
        }
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
