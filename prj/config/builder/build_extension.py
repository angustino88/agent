from .extension.setup_file_generator import generate_setup_file

class BuildExtension:
    """
    Extension hook for build process.
    Allows custom actions before and after the main build.
    """
    def __init__(self, app_dir: str, app_name: str, app_version: str, build_args: list[str]):
        self.app_dir = app_dir
        self.app_name = app_name
        self.app_version = app_version
        self.build_args = build_args

    def before(self) -> None:
        """
        Hook for actions to perform before the build.
        Override or extend as needed.
        """
        pass

    def after(self) -> None:
        """
        Hook for actions to perform after the build.
        Generates setup.bat in the app directory.
        """
        generate_setup_file(self.app_name, self.app_dir)
