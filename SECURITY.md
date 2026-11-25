# Security policy

Katip's job is to keep personal data from leaving the user's device. A security problem here is anything
that defeats that, so please report it privately.

## What to report

- A detected value that is still readable after masking (in the text, the file, its metadata, a file name).
- A way around the leak check, which should refuse to return text that still contains a detected value.
- Case keys, the vault or a connection's stored login being readable by another user or program.
- Any network request the apps make that is not listed in [NETWORK.md](NETWORK.md), or that sends more
  than the page says.
- Prompt-injection paths in Kalkan (the MCP server) that make Claude read files outside the case folders, or
  get real values back from `restore_to_file`.
- A local API (Klasör, the Katip engine) that another web page or program on the computer can call without
  its token.

A name the model simply misses on ordinary text is an accuracy problem, not a security one. Please report it
with the *Hata bildir* button or a [mistake report](https://github.com/fikrifirat/katip/issues/new/choose),
with fake values.

## How to report

Use GitHub's private vulnerability reporting on this repository (*Security → Report a vulnerability*), or
e-mail **fikrifirat@gmail.com** with "Katip security" in the subject. Never include real personal data; a
synthetic example that shows the problem is enough.

You can expect an acknowledgement within 7 days, a first assessment within 14 days, and credit in the release
notes when it is fixed, unless you'd rather stay anonymous. Please give us a reasonable time to fix it before
you publish.

## Supported versions

The latest release of each part (web app, Kalkan, Klasör, the SDKs) gets security fixes. Older versions don't.
