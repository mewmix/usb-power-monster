# USB Power Monster

Cross-platform USB storage power-state torture harness for engineering regression.

USB Power Monster is built to answer one question with hard evidence:

> Did a USB power-management configuration actually fix the state machine, or did it merely avoid the failing path?

## Targets

- USB 3.x U0/U1/U2/U3 behavior
- USB 2.0 L1 and selective suspend
- suspend/resume abuse around real file I/O
- SHA-256 integrity verification before and after every transition
- wake latency and I/O latency measurement
- JSONL per-iteration evidence
- Linux kernel and Windows event/ETW failure capture
- Linux sysfs LPM/runtime-suspend controls
- Windows USBLPM U1/U2 control when available

The default workload operates only inside `.usb-power-monster` beneath a user-selected mounted DUT directory. Raw-device destructive writes are intentionally not part of the initial harness.

## Install

```bash
python -m pip install -e .
```

## Linux

```bash
sudo usb-power-monster /mnt/dut \
  --sysfs-device /sys/bus/usb/devices/2-3 \
  --states U1,U2,U3 \
  --cycles 10000 \
  --payload-mib 256 \
  --idle-ms 100
```

For USB2:

```bash
sudo usb-power-monster /mnt/dut \
  --sysfs-device /sys/bus/usb/devices/1-3 \
  --states L1,SUSPEND \
  --cycles 10000
```

## Windows

Run elevated. Supply Microsoft's USBLPM executable when explicit U1/U2 control is required:

```powershell
usb-power-monster.exe E:\ `
  --usblpm C:\Tools\USBLPM.exe `
  --states U1,U2,U3 `
  --cycles 10000 `
  --payload-mib 256
```

## Evidence discipline

The harness distinguishes:

- `requested` — the host/tool requested or enabled a state;
- `host-reported` — the OS reported a runtime/suspend state;
- `observed` — reserved for trace/analyzer evidence proving physical link state;
- `inferred` — behavior suggests a transition but does not prove it.

It therefore will not claim that enabling U1/U2 or selective suspend proves that the wire actually entered U1/U2/U3.

See [docs/CRUSADE.md](docs/CRUSADE.md) for the full A/B regression methodology and escalation plan.
