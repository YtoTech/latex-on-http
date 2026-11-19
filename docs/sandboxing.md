# Compilation sandboxing

Compilations use Bubblewrap by default. The complete Latexmk process tree runs with:

* only the current workspace mounted read/write at `/work`;
* TeX, fonts, shared libraries and minimal configuration mounted read-only;
* standard executable directories rebuilt from a curated list;
* private PID, IPC, UTS and network namespaces, with networking disabled;
* dropped capabilities and a scrubbed environment;
* process-group termination on compilation timeout.

## Shell escape and `minted`

`minted` needs `options.compiler.shell_escape=true`. This exposes the curated shell, Python and Pygments entry points and enables TeX shell escape.

Unrestricted shell escape plus an interpreter permits arbitrary programs **inside the sandbox**; the filesystem, namespace and network restrictions remain the security boundary. Keep it disabled unless the document requires it.

## Executable allowlist

The executable allowlist covers conventional `/usr/bin`-style entry points. A minimal compiler-only image or per-job AppArmor policy is still recommended if execution of helper binaries elsewhere in the read-only runtime must also be prohibited.

## Runtime requirements

The image installs `bubblewrap` and `python3-pygments`. The host must allow Bubblewrap to create unprivileged user and mount namespaces.

Do not grant the API container broad `SYS_ADMIN` access or expose the Docker socket merely to bypass a namespace restriction. A missing Bubblewrap executable returns HTTP 503 with `SANDBOX_UNAVAILABLE`; there is no automatic unsandboxed fallback.

Verify the built service by running the real sandbox test and compiling a `minted` document. `docker-compose.test.yml` sets `LATEX_REQUIRE_SANDBOX_TESTS=1`, making a missing Bubblewrap executable a test-suite error rather than an ignored skip. A deployment where Bubblewrap cannot create namespaces must be fixed at the host/container policy level before accepting untrusted compilations.

For **trusted local development only**, isolation can be disabled explicitly:

```sh
export LATEX_SANDBOX_BACKEND=none
```

## Configuration

Server-side configuration variables:

* `LATEX_BWRAP_PATH`: explicit Bubblewrap executable path;
* `LATEX_SANDBOX_EXTRA_COMMANDS`: additional commands for all jobs;
* `LATEX_SHELL_ESCAPE_EXTRA_COMMANDS`: additional commands only for shell-escape jobs;
* `LATEX_SANDBOX_READ_ONLY_PATHS`: space-separated replacement for the default read-only runtime paths;
* `MAX_PDF_SIZE` and `MAX_LOG_FILE_SIZE`: maximum generated file sizes returned by the service.

## Resource limits

Bubblewrap does not provide per-job CPU, memory, PID or disk quotas. Production deployments should add delegated cgroups or a separate per-job container runner for those controls.
