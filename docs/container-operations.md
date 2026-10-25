# Container delivery and recovery

The image runs as UID/GID10001, with the application and dependencies immutable.
Only `/data` needs persistent write access; `/tmp` can be a bounded tmpfs. Both
Python stages and the uv binary image are pinned by registry-verified digests.
The build installs only locked runtime dependencies, without an editable source
mount or development tools. Dependabot proposes Docker digest updates.

## Local smoke deployment

```sh
docker build --tag shortlink:local .
docker volume create shortlink-data
docker run --detach --name shortlink --publish 127.0.0.1:8000:8000 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --mount source=shortlink-data,target=/data \
  --env SHORTLINK_BASE_URL=http://127.0.0.1:8000 shortlink:local
python tests/container_smoke.py create
docker restart shortlink
python tests/container_smoke.py persisted
```

The smoke check deliberately uses a fixed record and should run on a fresh test
volume. It exercises the actual HTTP server and verifies the same SQLite record
survives restart. The CI workflow also checks the configured non-root UID and runs
with a read-only root filesystem, dropped capabilities and no new privileges.

## Release evidence

PRs, main changes, manual runs and a weekly schedule build and smoke-test the image.
Trivy fails validation on any detected CRITICAL vulnerability, including unfixed
ones. The database changes over time; a passing historical scan is not a permanent
clean bill of health. The workflow retains a scan report and CycloneDX SBOM.

Only a published stable semantic release can publish to GHCR. Its source commit
must already be an ancestor of reviewed main. A separate job loads and pushes the
exact image that passed smoke/scan, then attaches GitHub OIDC build provenance and
SBOM attestations to its registry digest. It uploads the SBOM and scan to the
release. PR validation receives no registry-write token or provider credential.

The first published release, [v0.1.0](https://github.com/Abdel-Abdelaal/shortlink/releases/tag/v0.1.0),
passed [hosted build, smoke, scan and publication](https://github.com/Abdel-Abdelaal/shortlink/actions/runs/40148403921).
Anonymous registry access and both attestations were independently verified with
the GitHub CLI. The tested image is:

```text
ghcr.io/abdel-abdelaal/shortlink@sha256:e91a978359cdf1b6bfef0c4f20314f2c336c70387c641bf0c6642f8a394333ef
```

Verify provenance and the CycloneDX SBOM before using that exact image:

```sh
gh attestation verify oci://ghcr.io/abdel-abdelaal/shortlink@sha256:e91a978359cdf1b6bfef0c4f20314f2c336c70387c641bf0c6642f8a394333ef \
  --repo Abdel-Abdelaal/shortlink
gh attestation verify oci://ghcr.io/abdel-abdelaal/shortlink@sha256:e91a978359cdf1b6bfef0c4f20314f2c336c70387c641bf0c6642f8a394333ef \
  --repo Abdel-Abdelaal/shortlink --predicate-type https://cyclonedx.org/bom
```

The release also contains `sbom.cdx.json` and `trivy.json`. These results establish
the published artifact's identity and checks at release time; they do not establish
that a public service is deployed or that future vulnerability scans will pass.

## Backups and rollback

SQLite and this image are designed for one service instance with persistent local
storage. Multiple independently writable replicas are outside this design.
Before upgrades, quiesce writes and make a consistent backup with SQLite's backup
API; do not copy only a live database file while WAL transactions are outstanding.
Store backups outside the service volume and test restoring them to a fresh volume.

Record the previous verified image digest, configuration and database schema
version before each deployment. Roll back by stopping the service, restoring a
verified backup if the schema is incompatible, and starting the previous digest
with the same hardened runtime flags. Re-run readiness and a dedicated test-record
smoke check before admitting traffic. Never overwrite the only remaining backup.

## Hosting boundary

No public deployment target is configured. This is a local engineering demo: the
link management endpoints do not provide authentication, rate limiting or abuse
moderation. Keep the port bound to loopback until a reviewed deployment adds those
controls, TLS, trusted ingress configuration, monitoring and an explicit recovery
objective. The application does not fetch target URLs; it redirects clients.
`--no-proxy-headers` avoids trusting forwarded client headers by default.

## Base image remediation evidence

The first hosted scan blocked the Bookworm runtime for CVE-2025-7458 (SQLite) and
CVE-2023-45853 (zlib). The runtime and builder now use digest-pinned Trixie, where
Debian reports fixed packages for both findings:
[SQLite tracker](https://security-tracker.debian.org/tracker/CVE-2025-7458),
[zlib tracker](https://security-tracker.debian.org/tracker/CVE-2023-45853).
The gate remains unchanged and has no vulnerability suppression file. The rebuilt
image passed the unchanged critical-severity gate in release run40148403921, linked
above. Weekly rebuilding and scanning re-evaluates the current vulnerability database.
