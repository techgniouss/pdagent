"""Live remote-desktop package.

All heavy dependencies (aiohttp, mss, qrcode, xxhash) are imported lazily
inside the functions that need them. Importing this package must NOT pull
any of them — that keeps idle bot startup cost unchanged.
"""
