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

Rootless Docker and rootless Podman are the intended deployment targets. The base Compose files use their normal runtime policies; any Bubblewrap-specific overrides belong in `docker-compose.rootless.yml`. A missing Bubblewrap executable returns HTTP 503 with `SANDBOX_UNAVAILABLE`; there is no automatic unsandboxed fallback.

Bubblewrap always creates a mount namespace and uses `pivot_root` to finish its private root. Docker's default seccomp profile does not allow `pivot_root`, including when `SYS_ADMIN` is present. The rootless override therefore loads `container/seccomp-bubblewrap.json`, which retains Docker's pinned deny-by-default baseline and adds only that one syscall. It does not use `seccomp=unconfined`, `privileged`, `systempaths=unconfined`, or `unmask=ALL`.

The sandbox deliberately does **not** mount procfs. Container runtimes mask parts of the outer `/proc`, which can cause `bwrap: Can't mount proc on /proc: Operation not permitted` in a nested PID namespace. TeX and the supported helpers do not need procfs, so omitting it avoids widening access to host namespace paths. The private PID namespace remains enabled for process-tree containment.

Latexmk requires `env`, Perl, and `/bin/sh` for its own process launching, including with TeX's `-no-shell-escape`. Those fixed launchers are always mounted, with the `/bin` to `usr/bin` symlink retained. Python, Pygments, and any extra configured helpers remain restricted to shell-escape jobs.

The Ghostscript conversion wrappers are shell scripts, so the curated tools include `ps2pdf → ps2pdf14 → ps2pdfwr → gs`, plus `dirname` for locating the next wrapper and `basename` for deriving default output filenames. This does not mount general coreutils, Curl, or `/usr/bin` wholesale.

Recreate the service after changing security or namespace configuration—rebuilding its image or running `docker compose restart` alone does not update an existing container's runtime settings:

```sh
docker compose up -d --build --force-recreate latex
```

If namespace creation is denied, check the host's user-namespace controls (including `kernel.unprivileged_userns_clone`, `user.max_user_namespaces`, and AppArmor restrictions) and ensure kernel user namespaces are enabled.

### Rootless Docker and Podman

If the `No permissions to create a new namespace` error occurs on a rootless Docker or Podman host, select the supplied rootless override in the repository's local `.env` file:

```dotenv
COMPOSE_FILE=docker-compose.yml:docker-compose.rootless.yml
```

The `.env` file is ignored by Git. See `.env.example` for a template. Docker Compose reads this file directly, so the usual development commands use both files:

```sh
docker compose up -d --build --force-recreate latex
# Or: make dev
```

Linux/macOS uses `:` to separate Compose filenames. Use the platform's `COMPOSE_PATH_SEPARATOR` if running on a platform that uses a different separator.

This adds `SYS_ADMIN` to the API container **inside the rootless container runtime's user namespace**. According to [Docker's rootless limitations](https://docs.docker.com/engine/security/rootless/troubleshoot/#known-limitations), capabilities added this way apply only to resources governed by the container's user namespace; they do not grant capabilities in the host's initial user namespace. Compilation children still run as UID/GID 65534 in their Bubblewrap sandbox with all capabilities dropped.

Do not apply this override to rootful Docker as a general workaround. It is an explicit trade-off for the nested user namespaces used by rootless Docker, not a substitute for checking host policy. It does not require `privileged` or `seccomp=unconfined`.

The Makefile reads the same `.env` and carries the non-base overrides into the test stack. All `test-docker-compose-*` targets use `docker-compose.test.yml` followed by the selected overrides, so the usual commands work unchanged:

```sh
make test-docker-compose-build
make test-docker-compose-start
make test
make test-docker-compose-stop
```

You can inspect the selected files without starting containers with `make -n test-docker-compose-start`. `COMPOSE_TEST_FILES` can also be set to an explicit space-separated list if the test stack needs a different set of Compose files.

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

With `SENTRY_DSN` configured, recognized sandbox infrastructure failures are also reported to Sentry. This covers missing curated executables, wrapper-process permission failures, and Bubblewrap startup failures, including requests that still return their normal 400 or 503 error response. Events have stable `sandbox.issue` and `sandbox.binary` tags, a stable fingerprint for grouping, the compiler, workspace ID, and a single recognized diagnostic line. Inherited Sentry/Flask request context is deliberately retained to show the use case that triggered the failure. It may include request parameters or submitted TeX/source data, and should follow your Sentry retention and redaction policy. Full compiler logs are not added as a separate attachment. Ordinary document errors such as missing `.tex` or `.sty` files do not generate these reports.

When `SENTRY_DSN` is not configured, reporting is disabled and compilation behavior is unchanged. A Sentry reporting failure is logged but never replaces the compiler result.

## Resource limits

Bubblewrap does not provide per-job CPU, memory, PID or disk quotas. Production deployments should add delegated cgroups or a separate per-job container runner for those controls.
