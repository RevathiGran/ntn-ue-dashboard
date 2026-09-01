"""
test_sender.py
--------------
Run this ON PC-1 to send a few dummy packets to the dashboard over TCP --
lets you verify the Ethernet link end-to-end before touching any real OAI
code. Needs only Python 3, no extra packages.

Usage (on PC-1):
    python3 test_sender.py --host <PC-2's IP> --port 9000

Find PC-2's IP by running `hostname -I` or `ip addr` ON PC-2.
Make sure the dashboard is already running on PC-2 first:
    python main.py --transport socket --tcp-port 9000
"""

import argparse
import socket
import struct
import time


def build_packet(dtype: int, lat=0.0, lon=0.0, alt=0.0, x=0.0, y=0.0, z=0.0,
                  vx=0.0, vy=0.0, vz=0.0, dl_mbps=0.0, ul_mbps=0.0,
                  ta_ms=0.0, ta_drift=0.0, ta_drift_var=0.0,
                  ue_ip="", timestamp=None):
    if timestamp is None:
        timestamp = int(time.time() * 1000)
    ip_bytes = ue_ip.encode("ascii", "ignore")[:31].ljust(32, b"\x00")
    body = struct.pack(
        "<BB14d32sQ",
        dtype, 0,
        lat, lon, alt, x, y, z, vx, vy, vz,
        dl_mbps, ul_mbps, ta_ms, ta_drift, ta_drift_var,
        ip_bytes, timestamp,
    )
    payload = b"\xAA\x55" + body
    checksum = sum(payload) % 256
    return payload + struct.pack("<B", checksum)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True, help="PC-2's IP address")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    print(f"Connecting to dashboard at {args.host}:{args.port} ...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((args.host, args.port))
    print("Connected. Sending test packets (Ctrl+C to stop)...")

    t = 0
    try:
        while True:
            t += 1
            # DataType.UE_POSITION = 2
            pkt = build_packet(2, lat=12.9716 + t * 0.0001, lon=77.5946, alt=920.0,
                                x=1181000, y=5342000, z=1424000, ue_ip="10.0.1.23")
            s.sendall(pkt)
            print(f"  sent UE_POSITION #{t}: lat={12.9716 + t*0.0001:.6f}")

            # DataType.VELOCITY = 4
            pkt = build_packet(4, vx=0.5, vy=-0.2, vz=0.0)
            s.sendall(pkt)

            # DataType.THROUGHPUT = 5
            pkt = build_packet(5, dl_mbps=80.0, ul_mbps=20.0)
            s.sendall(pkt)

            # DataType.NTN_TA = 6
            pkt = build_packet(6, ta_ms=6.2, ta_drift=1.1, ta_drift_var=0.002)
            s.sendall(pkt)

            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        s.close()


if __name__ == "__main__":
    main()
