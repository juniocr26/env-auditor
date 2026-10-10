# Filesystem safety and plaintext recovery

[English](filesystem-boundaries.md) | [Português brasileiro](../../pt-BR/security/filesystem-boundaries.md)

Static source review: 2026-10-10. Implemented facts, general theory and hypothetical changes are distinguished below. Runtime commands were not executed.

Inputs must be regular files; discovery skips symlinks and processing checks file status again. Parsing rejects invalid UTF-8, NUL bytes, malformed assignments and unterminated quotations. These checks reduce accidental traversal and malformed transformations; there is no file locking or race-free descriptor-based traversal. A path can change between checking and using it. Do not describe this as an adversarial filesystem sandbox.

Values are omitted from terminal output, but paths and key names remain visible. Reference values are trusted literals: the program does not detect secrets. Backups contain exact original bytes and removed blocks in plaintext. Session directories use 0700, files use 0600, and the backup-root ignore file contains `*`. This reduces ordinary access and accidental Git inclusion, but does not encrypt backups, protect against the same user or define retention. Existing target permission bits are preserved; ownership, ACLs and extended attributes are not.

A changed existing target is backed up before replacement. The same-directory temporary file is flushed and fsynced, chmodded and replaced using `os.replace`. This gives individual-file replacement, not a multi-file transaction. The directory is not fsynced, and concurrent writers can be overwritten. Stronger durability would require a directory-sync design; writer coordination would require locking and change detection. Both are hypothetical changes. No real environment or backup was inspected during this documentation review.
