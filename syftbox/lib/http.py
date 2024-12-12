import platform

import distro

from syftbox import __version__

# keep these as bytes
HEADER_SYFTBOX_VERSION = b"x-syftbox-version"
HEADER_SYFTBOX_PYTHON = b"x-syftbox-python"
HEADER_SYFTBOX_USER = b"x-syftbox-user"
HEADER_OS_NAME = b"x-os-name"
HEADER_OS_VERSION = b"x-os-ver"
HEADER_OS_ARCH = b"x-os-arch"

_PYTHON_VERSION = platform.python_version()

# OS info
uname = platform.uname()
if uname.system == "Darwin":
    _OS_NAME = "MacOS"
else:
    _OS_NAME = uname.system


def get_os_version(os_name: str = None) -> str:
    if os_name == "Linux":
        return distro.name(pretty=True)
    elif os_name == "Windows":
        return platform.win32_ver()[0]
    elif os_name == "MacOS":
        return platform.mac_ver()[0]
    else:
        return "Unknown"


_OS_VERSION = get_os_version(_OS_NAME)  # e.g. '6.8.0-49-generic'
_OS_ARCH = uname.machine  # e.g. 'x86_64', 'arm64', 'aarch64', etc.

SYFTBOX_HEADERS = {
    HEADER_SYFTBOX_VERSION: __version__,
    HEADER_SYFTBOX_PYTHON: _PYTHON_VERSION,
    HEADER_OS_NAME: _OS_NAME,
    HEADER_OS_VERSION: _OS_VERSION,
    HEADER_OS_ARCH: _OS_ARCH,
}
