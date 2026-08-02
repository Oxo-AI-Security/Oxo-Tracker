---
name: release-oxo-tracker
description: Commit, build, validate, and publish Oxo Tracker Windows Preview releases, review the Oxo-Tracker-Releases README when release policy changes, and finally update the Alibaba Cloud OSS latest.json manifest. Use when asked to package, release, publish, update, or repair an Oxo Tracker desktop release or its OSS update metadata.
---

# Release Oxo Tracker

Run the complete release workflow from the Oxo Tracker workspace. Keep installers on GitHub Releases and store only `stable/latest.json` in OSS.

## Non-negotiable gates

- Treat the source repository, release repository, GitHub Release, and OSS object as four separate states. Verify each state before advancing.
- Never print, persist, commit, or transmit the updater private key, its password, GitHub credentials, Alibaba Cloud credentials, or endpoint API keys.
- Never commit unrelated user changes. Inspect every changed and untracked path before staging. Stop if ownership or intent is ambiguous.
- Never publish from a dirty source worktree. Commit the intended source changes and push them before building.
- Never reuse an already-published version for different bytes. Select a higher version whenever the application or release artifacts changed.
- Publish as Preview/Pre-release while Authenticode is unavailable. Do not describe an unsigned installer as stable.
- Update OSS only after the GitHub release is public and all local release gates pass. A failed release must leave the previous OSS manifest intact.
- Do not upload installers, signatures, checksums, SBOMs, or notices to OSS. Upload only `latest.json`.

## 1. Inspect and commit the source

1. Resolve the workspace with `git rev-parse --show-toplevel` and confirm the `origin` repository is `Oxo-AI-Security/Oxo-Tracker`.
2. Fetch `origin`, inspect `git status --short`, `git diff`, and `git diff --cached`, and check untracked files for secrets or generated artifacts.
3. Run relevant tests for the changed code before committing. The desktop build will run the full backend and frontend suites again unless an explicitly justified recovery uses `-SkipTests`.
4. Stage only intended source and Skill changes. Use a concise conventional commit message. Do not create an empty commit.
5. Push the current source branch. Formal releases normally use `main`; do not silently release an unmerged feature branch.

## 2. Choose the release version

Run:

```powershell
& .\.codex\skills\release-oxo-tracker\scripts\Resolve-OxoReleaseVersion.ps1
```

Use an explicitly requested semantic version if the user supplied one; otherwise use the returned next patch version. Query GitHub again immediately before creation. If that tag is now published, resolve a new version rather than overwriting it.

When the requested version already exists, compare the published asset set, `latest.json`, checksum, and local artifacts. Reuse it only to finish an interrupted metadata/OSS step with identical bytes. Skip the expensive build when a fully validated local release already matches the public release.

## 3. Review the release repository README

Clone or update `https://github.com/Oxo-AI-Security/Oxo-Tracker-Releases.git` under `.desktop-build/Oxo-Tracker-Releases-repo`. Read the complete README before publishing.

Change the README only when a durable fact changed, including:

- download or installation instructions;
- supported operating systems or architecture;
- Preview, stable, or Authenticode policy;
- local-data preservation or updater behavior;
- the public OSS updater endpoint;
- artifact verification instructions or the required asset set.

Do not rewrite it merely because the patch version changed. Prefer version-neutral command examples. If an update is needed, commit and push it in the release repository before publishing the release.

## 4. Build and validate

Run the wrapper from the workspace root:

```powershell
& .\.codex\skills\release-oxo-tracker\scripts\Invoke-OxoDesktopBuild.ps1 -Version 0.2.2
```

The wrapper securely prompts for the updater-key password, invokes the canonical `scripts/build-desktop.ps1`, generates release notes and build information, and independently verifies the updater signature. Do not pass a plaintext password on a command line.

Read `artifacts/desktop-release/<version>/RELEASE-NOTES.md` after generation. Improve user-facing wording when the Git history is too technical, while keeping claims evidence-based. Re-run:

```powershell
& .\.codex\skills\release-oxo-tracker\scripts\Test-OxoRelease.ps1 -Version 0.2.2 -MarkVerified
```

Require exactly the nine allowlisted assets, a matching SHA-256, matching updater signature and URL, valid product/file version, consistent Moonshot manifest counts, and a cryptographically valid updater signature.

## 5. Publish the GitHub Preview release

Run:

```powershell
& .\.codex\skills\release-oxo-tracker\scripts\Publish-OxoGithubRelease.ps1 -Version 0.2.2
```

The script creates or resumes a draft, uploads only the allowlisted files, verifies GitHub-reported asset sizes, and publishes only when the complete set is present. It is idempotent for an already-published release only when all expected asset names and sizes match. Never delete or mutate an existing published release automatically.

After publishing, verify the public release URL and installer URL without relying only on the authenticated API response.

## 6. Update OSS last

Run only after Step 5 succeeds:

```powershell
& .\.codex\skills\release-oxo-tracker\scripts\Publish-OxoOssManifest.ps1 -Version 0.2.2
```

The script discovers the configured `ossutil`, uploads `latest.json` with public-read, JSON content type, and `no-cache`, then reads the public HTTPS object back and compares its bytes and semantic fields with the local manifest. It intentionally does not call `ls`, `stat`, or `GetObjectAcl`; the configured RAM identity needs only the minimal object-write permission.

## 7. Report and recover

Report the source commit, version, test result, installer SHA-256, Authenticode state, GitHub release URL, OSS URL, and whether the release README changed.

For an interrupted run, inspect existing state and resume at the earliest incomplete gate. Do not rebuild solely because GitHub upload or OSS publication failed. Do not update OSS when GitHub is draft, missing assets, or serves different release metadata.
