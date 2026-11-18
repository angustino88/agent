class VersionConfig:
    """
    Application version configuration.

    Versioning scheme: <major>.<minor>.<patch>
      - major: Major release, new UI/design/architecture, many new features.
      - minor: Minor release, some features or functionalities added.
      - patch: Bug fix release.

    Example: 1.0.2 -> major=1, minor=0, patch=2
    """
    APP_VERSION = '2.7.0'

    CHANGELOG = [
        "Improved application stability, installation, and multi-user support",
        "Bug fixes and general improvements",
    ]

    REQUIRES = {
        "os": ["windows"],
        "arch": ["x86_64", "AMD64"],
    }