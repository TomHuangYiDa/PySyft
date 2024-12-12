import platform

from syftbox import __version__

# keep these as bytes as otel hooks return headers as bytes
HEADER_SYFTBOX_VERSION = b"x-syftbox-version"
HEADER_SYFTBOX_PYTHON = b"x-syftbox-python"
HEADER_SYFTBOX_USER = b"x-syftbox-user"
HEADER_OS_NAME = b"x-os-name"
HEADER_OS_VERSION = b"x-os-ver"
HEADER_OS_ARCH = b"x-os-arch"

_PYTHON_VERSION = platform.python_version()
_UNAME = platform.uname()
_OS_NAME = ""
_OS_VERSION = ""
_OS_ARCH = _UNAME.machine

if _UNAME.system == "Darwin":
    _OS_NAME = "macOS"
    _OS_VERSION = platform.mac_ver()[0]
elif _UNAME.system == "Linux":
    import distro

    _OS_NAME = distro.name()
    _OS_VERSION = distro.version(best=True)
elif _UNAME.system == "Windows":
    _OS_NAME = _UNAME.system
    _OS_VERSION = platform.win32_ver()[0]

SYFTBOX_HEADERS = {
    "User-Agent": f"SyftBox/{__version__} (Python {_PYTHON_VERSION}; {_OS_NAME} {_OS_VERSION}; {_OS_ARCH})",
    HEADER_SYFTBOX_VERSION: __version__,
    HEADER_SYFTBOX_PYTHON: _PYTHON_VERSION,
    HEADER_OS_NAME: _OS_NAME,
    HEADER_OS_VERSION: _OS_VERSION,
    HEADER_OS_ARCH: _OS_ARCH,
}
