# USB Power Monster

Cross-platform USB storage power-state torture harness for engineering regression.

Targets:

- USB 3.x U0/U1/U2/U3 behavior
- USB 2.0 L1 and selective suspend
- suspend/resume abuse around real file I/O
- continuous data-integrity verification
- transition, latency, disconnect, timeout and kernel/event logging
- Linux and Windows backends

The default workload is **non-destructive** and operates only inside a user-selected directory on the DUT. Raw-device destructive testing is intentionally not implemented in the initial harness.

## Status

Initial implementation in progress.
