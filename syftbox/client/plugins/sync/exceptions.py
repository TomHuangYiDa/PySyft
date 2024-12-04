from syftbox.client.exceptions import SyftBoxError, SyftServerError


class FatalSyncError(SyftBoxError):
    """Base exception to signal sync should be interrupted."""

    pass


class SyncEnvironmentError(FatalSyncError):
    """the sync environment is corrupted (e.g. sync folder deleted), syncing cannot continue."""

    pass


class SyftPermissionError(SyftServerError):
    pass


class SyncValidationError(SyftBoxError):
    pass
