# Security Policy

## Supported Versions

Only the default branch and the latest release are maintained. Older snapshots are not patched.

## Reporting a Vulnerability

Please **do not** open a public issue for a security problem.

Use GitHub's private vulnerability reporting instead:

https://github.com/rngfbbbffhjgggd-commits/bili-content-extractor/security/advisories/new

The report stays private between you and the maintainer until a fix is published. This is a personal project, so there is no SLA and no paid support — expect a first reply within roughly a week, and please include a repro so the fix can be verified.

## Scope

This project downloads and converts media by invoking local tools (`ffmpeg`, `yt-dlp`, local ASR models).

In scope:
- command injection or path traversal from untrusted input (video titles, playlist metadata, subtitle files)
- output written outside the directory you selected
- leakage of local cookies or credentials

Out of scope:
- vulnerabilities in the upstream video platform
- defects in the ASR model weights shipped by third parties

## What helps a report

- the version or commit you tested
- steps to reproduce, or a minimal proof of concept
- the impact you believe it has (local file write, credential leak, code execution, ...)

## Out of scope

- issues that only reproduce with an unsupported Python / OS / dependency version
- findings from automated scanners with no demonstrated impact
- bugs in third-party services this project merely talks to
