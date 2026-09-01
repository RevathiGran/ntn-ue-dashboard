"""
OAI NTN Monitoring Dashboard -- entry point.

Usage:
    python main.py --mock                                  # simulated data, no hardware
    python main.py --transport serial                      # USB, auto-detect device
    python main.py --transport serial --device /dev/ttyUSB0
    python main.py --transport socket --tcp-port 9000       # Ethernet: listen for PC-1
"""

import argparse
import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(description="OAI NTN Monitoring Dashboard")
    parser.add_argument("--transport", choices=["serial", "socket"], default="serial",
                         help="How PC-1 delivers data: 'serial' (USB) or 'socket' (Ethernet/TCP). Default: serial")
    parser.add_argument("--device", default=None, help="[serial] Serial device path (e.g. /dev/ttyUSB0). Auto-detected if omitted.")
    parser.add_argument("--baud", type=int, default=115200, help="[serial] Baud rate (default 115200)")
    parser.add_argument("--host", default="0.0.0.0", help="[socket] Address to listen on (default 0.0.0.0 = all interfaces)")
    parser.add_argument("--tcp-port", type=int, default=9000, help="[socket] TCP port to listen on (default 9000)")
    parser.add_argument("--mock", action="store_true", help="Run with simulated data, no PC-1 connection required")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("OAI NTN Monitoring Dashboard")
    window = MainWindow(
        transport=args.transport, port=args.device, baudrate=args.baud,
        host=args.host, tcp_port=args.tcp_port, mock=args.mock,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
