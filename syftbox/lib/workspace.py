from syftbox.lib.types import PathLike, to_path


class SyftWorkspace:
    """
    A Syft workspace is a directory structure for everything stored by the client.
    Each workspace is expected to be unique for a client.

    ```txt
        data_dir/
        ├── apps/                       <-- installed apps
        ├── plugins/                    <-- plugins data
        └── datasites/                  <-- synced datasites
            ├── user1@openmined.org/
            │   └── apps_pipeline/
            └── user2@openmined.org/
                └── apps_pipeline/
    ```
    """

    def __init__(self, data_dir: PathLike):
        self.data_dir = to_path(data_dir)
        """Path to the root directory of the workspace."""

        # datasites dir
        self.datasites = self.data_dir / "datasites"
        """Path to the directory containing datasites."""

        # plugins dir
        """Path to the directory containing plugins."""
        self.plugins = self.data_dir / "plugins"

        # apps dir
        self.apps = self.data_dir / "apps"
        """Path to the directory containing apps."""

    def mkdirs(self):
        self.datasites.mkdir(parents=True, exist_ok=True)
        self.plugins.mkdir(parents=True, exist_ok=True)
        self.apps.mkdir(parents=True, exist_ok=True)
