# PROBLEM_REVIEW

Status: resolved

## 2026-07-29: Open-data Clone Timeout

### Observe

`git clone --depth 1 https://github.com/hudl/open-data.git` failed after 75
seconds with an HTTPS connection timeout. A subsequent read-only
`git ls-remote` failed with a receive timeout.

### Diagnose

- The repository URL is valid and GitHub API authentication had succeeded.
- The clone process exited and Git removed its incomplete target directory.
- Repeated Git HTTPS access establishes an external connectivity failure rather
  than a local path, permission, or repository-state error.
- The original sync script could still leave an ambiguous target if a process
  were forcefully interrupted outside Git's own cleanup.

### Repair

Clone into a `mktemp` directory, remove that exact temporary directory on
failure, and move the repository into its final path only after clone success.
Validate an existing clone has a `HEAD` before pulling.

### Verification

- Local tests clone from a fixture repository, verify the metadata file is
  present, exclude an unselected event file, update an existing clone, and
  remove temporary directories after failure.
- The real upstream partial clone completed over SSH at commit
  `b0bc9f22dd77c206ddedc1d742893b3bbe64baec`.
- The checkout occupies approximately 1.5 MB and contains the upstream README,
  license, and `data/competitions.json`.

### Remaining Delta

Git HTTPS remained unavailable during bootstrap, so this machine's ignored
upstream clone uses the authenticated SSH remote. The public sync script keeps
HTTPS as its portable default and supports an environment override.
