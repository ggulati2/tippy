# Security policy

Tippy is a children's learning app that runs only on the family's own computer. Reports about anything that could put a child's privacy or safety at risk are taken seriously.

## Reporting a problem

Please **do not open a public issue** for a security problem. Use GitHub's private reporting instead:
**Security tab → Report a vulnerability** (https://github.com/ggulati2/tippy/security/advisories/new).

Include what you did, what you expected, what happened, and your Tippy version (the `VERSION` file). You will get a first answer within a week.

## What is in scope

- The child's name, or anything the child types, leaving the computer or reaching the online helper.
- Text from the online helper reaching the child without validation.
- Getting past the PIN, the daily limit or the exit protection.
- Another website or program on the same computer talking to Tippy's local server.
- Secrets (API key, PIN hash) appearing in the repository, a backup file, a log or the built zip.

## Supported versions

Only the latest release receives fixes.

## How Tippy is protected

The server listens on `127.0.0.1` only and checks the `Host` and `Origin` headers. The PIN is stored as a salted hash. All parent actions need a token that is kept only in memory. Online helper output is validated on the server and shown as plain text. The repository is scanned for secrets, CodeQL checks the code, and Dependabot watches the dependencies.
