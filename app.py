from latexonhttp.app import app

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Latex on HTTP.')
    parser.add_argument('--verbose', action='store_true', help='Print verbose logging to stdout', default=False)
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=8080, debug=args.verbose, threaded=True)
