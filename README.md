# OAI NTN Monitoring Dashboard

Real-time NOC-style dashboard for an OpenAirInterface NTN project. Runs on
PC-2, reads structured metadata packets from PC-1 (OAI) over USB serial,
and updates the UI live via a threaded signal/slot architecture — no
polling, no UI freezing.

## Run it right now (no hardware needed)
```bash
pip install -r requirements.txt
python main.py --mock
```
This runs the full dashboard against simulated UE/satellite/velocity data —
useful for building the demo narrative and testing the UI before PC-1 is
sending real packets.

## Run against real hardware

### Option A — Ethernet (recommended if PC-1 and PC-2 are separate machines)
Two full PCs can't talk over a bare USB cable (USB is host-to-device, not
host-to-host) unless you have a USB-to-serial adapter or bridge cable. If
both PCs can be put on the same network (Ethernet cable or shared WiFi),
this is the simpler path -- your original spec explicitly allows it.

**On PC-2 (dashboard):**
```bash
hostname -I          # note PC-2's IP address, e.g. 192.168.1.50
python main.py --transport socket --tcp-port 9000
```
The dashboard starts listening and shows "Listening on ... waiting for PC-1".

**On PC-1, verify the link before touching OAI at all:**
```bash
python3 test_sender.py --host 192.168.1.50 --port 9000
```
(Only needs Python 3, no packages.) You should see the dashboard's USB
Status card go green and UE position values start moving. **This is the
checkpoint to hit before writing any OAI integration code.**

**Once verified, wire it into OAI:** use `connect_to_dashboard()` /
`send_packet_tcp()` from `firmware_reference/oai_packet_sender_example.c`
(the TCP variant near the bottom of that file) in place of the test
sender, called from wherever OAI has live GPS-derived position/velocity.

### Option B — USB serial
If you have a USB-to-serial adapter (FTDI/CP210x/CH340) or a genuine
USB-to-USB bridge cable:
```bash
python main.py --transport serial                        # auto-detect
python main.py --transport serial --device /dev/ttyUSB0   # force a port
```
Reconnect handling is automatic — if the device disconnects mid-run, the
reader thread retries auto-detect/reconnect on its own.

## Project layout
```
main.py                          entry point / CLI args (serial, socket, or mock)
test_sender.py                   run on PC-1 to test the Ethernet link with no OAI/build step
core/packet_protocol.py          wire format: DataType enum, pack/unpack, checksum, framing
core/serial_reader.py            QThread: USB read loop, auto-detect, reconnect, mock generator
core/socket_reader.py            QThread: TCP server, accepts PC-1, same packet parsing/framing
ui/main_window.py                the dashboard window, all sections, packet -> UI switch(type) logic
ui/widgets.py                    glass cards, animated value labels, status dots
ui/theme.py                      dark NOC color palette + QSS
firmware_reference/
  oai_packet_sender_example.c    reference C code for PC-1 / OAI side (both USB serial and TCP variants)
```

## Wire format — read this before touching PC-1's sender code
Your original spec described a single `Metadata` struct sent raw over USB.
That works, but with **no framing**, a single dropped or corrupted byte on
the USB link permanently misaligns every packet after it — there's no way
to tell where one packet ends and the next begins. So this wraps the same
fields in a minimal frame:

```
[ 0xAA 0x55 (sync) | type (u8) | reserved (u8) | <fields below> | checksum (u8) ]
```
Fixed size: **157 bytes**, every packet, regardless of `type` — the sender
fills only the fields relevant to that type and zeroes the rest.

Fields (in order): latitude, longitude, altitude, x, y, z, velocity_x,
velocity_y, velocity_z, **dl_throughput_mbps, ul_throughput_mbps,
ta_common_ms, ta_common_drift, ta_common_drift_variant**, ue_ip[32],
timestamp. The bolded fields were added for radio DL/UL throughput and NTN
timing-advance tracking — see `DataType.THROUGHPUT` and `DataType.NTN_TA`
below.

- `THROUGHPUT` packets: fill `dl_throughput_mbps` / `ul_throughput_mbps`,
  zero the rest. Updates the Analytics card's DL/UL fields and chart.
- `NTN_TA` packets: fill `ta_common_ms` / `ta_common_drift` /
  `ta_common_drift_variant`, zero the rest. These map directly onto
  SIB19's `ta-Common` / `ta-CommonDrift` / `ta-CommonDriftVariant`.
  Updates the new "NTN — Timing Advance" card.

- The Python reader continuously scans for `0xAA 0x55` and resyncs
  automatically if it sees garbage — a glitch costs you one packet, not
  the rest of the session.
- The checksum (sum of all preceding bytes mod 256) catches the rarer case
  of corruption inside an already-aligned packet.
- Full byte-level layout is documented in `core/packet_protocol.py`, and
  the matching C struct is in `firmware_reference/oai_packet_sender_example.c`
  — sizes verified identical on both sides (157 bytes each, confirmed via
  `#pragma pack(1)` on the C side and `struct.calcsize` on the Python side).

**If you change any field, change it in both files together**, or the two
sides will silently desync.

## GPS source (PC-1 / OAI side)
Per your spec: replace OAI's hardcoded XYZ-location-file read with live GPS
input (bladeRF or u-blox GNSS module) — the existing GPS→coordinate
conversion logic in OAI stays as-is, only the input source changes. Once
you have live lat/lon/alt/XYZ/velocity in hand at that point in the OAI
code, call the `example_send_*` functions from `oai_packet_sender_example.c`
(or your own equivalent) to push them out over the USB serial link.

## What's implemented vs. placeholder
Implemented and live: connection status, UE position, UE velocity
(including derived total/speed/direction), satellite position + velocity,
packet counter, live log feed, auto-reconnect, mock mode.

Placeholders per your "future enhancements" list (wired into the UI, not
yet backed by real logic): packet loss % (needs sequence numbers in the
protocol — not in the current struct), multi-UE / multi-satellite (current
UI assumes one of each; extending to a list is straightforward given the
existing switch(type) structure, just needs a UE/satellite ID field added
to the packet), historical graphs beyond the rolling 60-sample velocity/
throughput charts already shown.

## Notes
- No real backdrop blur exists in Qt widgets, so "glassmorphism" here is
  approximated with translucent panel fills + soft drop shadows — reads as
  glass without needing a compositor.
- Tested headless (`QT_QPA_PLATFORM=offscreen`) end-to-end in mock mode:
  packets flow, all four sections update, animations render correctly.
  Hasn't been tested against a real USB device — do that early, not the
  night before judging.
