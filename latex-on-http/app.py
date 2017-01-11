from flask import Flask
app = Flask(__name__)

# xelatex -output-directory /root/latex/ /root/latex/sample.tex

@app.route("/")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    app.run(port=80)
