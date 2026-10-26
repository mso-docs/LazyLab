# Scan previous commits with Gitleaks

Gitleaks is already available as `/usr/bin/gitleaks` on the development machine used here. Check your installation with `command -v gitleaks` and `gitleaks version`.

## Run the history scan

From this checkout:

```bash
bash scripts/scan_history.sh
```

The script supports both newer `gitleaks git` and older `gitleaks detect` releases, scans all locally available refs, redacts detected values in output, and saves JSON to ignored `artifacts/security/history.json`. A nonzero exit means findings or an execution error; inspect the output. Do not treat errors as clean scans.

Equivalent commands:

```bash
# Current releases:
gitleaks git . --log-opts=--all --redact --report-path=artifacts/security/history.json

# Older installed releases:
gitleaks detect --source . --log-opts=--all --redact --report-path=artifacts/security/history.json
```

Create `artifacts/security/` before using the direct commands. History scanning examines commits, including files later deleted. It does not scan uncommitted changes. On current releases, `gitleaks dir . --redact` scans working files separately; older releases support `gitleaks detect --no-git --source . --redact`. A directory scan can include ignored local files and runtime artifacts, so keep reports private.

A shallow or incomplete clone contains only part of the history. Check with `git rev-parse --is-shallow-repository`. Where appropriate, fetch full history with `git fetch --unshallow`, then fetch the branches/tags you want audited. `--all` means refs available locally, not every historical object ever uploaded to GitHub or someone else's fork.

## Install on another machine

Use the [official Gitleaks installation documentation](https://github.com/gitleaks/gitleaks#installing) or [release downloads](https://github.com/gitleaks/gitleaks/releases). For a native Linux download, select the release archive matching `uname -s` and `uname -m`, download its checksum file from that same release, verify the archive's SHA-256, then extract the `gitleaks` executable. Place it in a directory on your PATH, for example `~/.local/bin`, and run `gitleaks version`. The download is not a pip package.

On macOS with Homebrew:

```bash
brew install gitleaks
```

With Docker on a machine where Docker is installed:

```bash
docker run --rm -v "$PWD:/repo:ro" ghcr.io/gitleaks/gitleaks:latest git /repo --log-opts=--all --redact
```

See [Gitleaks command documentation](https://github.com/gitleaks/gitleaks#usage) for version-specific options. The wrapper avoids needing an upgrade on the existing development machine.

## Latest local result

On October 25, 2026, the available **two commits** across local refs were scanned with no detected secrets. This is a bounded scanner result, not proof that no sensitive data exists. Commit author names/emails, private research, and personal paths require separate review; Gitleaks is not a general PII detector. A prior review identified the existing commit author email; ignoring a file does not remove it or other data from Git history.

If a real credential is found, revoke/rotate it first. Deleting the working file or adding `.gitignore` does not remove past commits. Review any history-rewrite plan before changing shared history; no history was rewritten here.
