class BuildConfig:
    #=========================================
    # Application entry script
    #=========================================
    APP_SCRIPT  = r'/src/main.py'

    #=========================================
    # Application name
    #   EMPTY = use script name
    #=========================================
    APP_NAME = 'LabMango'

    #=========================================
    # Application display name (human readable, can include spaces)
    #=========================================
    APP_DISPLAY_NAME = 'Lab Mango'

    #=========================================
    # NuGet / Chocolatey package metadata
    #=========================================
    NUGET_PACKAGE_ID = 'labmango'
    NUGET_AUTHORS = 'uah2hc'
    NUGET_DESCRIPTION = (
        'The LabMango agent runs on lab machines, providing remote access '
        'management and collecting data for a central server.'
    )
    NUGET_TAGS = 'labmango agent'
    NUGET_REQUIRE_LICENSE_ACCEPTANCE = False
    NUGET_COPYRIGHT = 'Copyright 2026 uah2hc'

    #=========================================
    # Path to application icon file
    #=========================================
    ICON_PATH = r'/assets/icons/mango.ico'

    #=========================================
    # Create zip package after build
    #   FALSE = do not zip
    #   TRUE  = create zip
    #=========================================
    ZIP = 'TRUE'

    #=========================================
    # Add version to package name
    #   FALSE = do not add version
    #   TRUE  = add version
    #=========================================
    VERSION_LABEL = 'TRUE'

    #=========================================
    # Sign the built package using the ed25519 private key at
    #    prj/config/keys/ed25519_priv.pem
    #   FALSE = do not sign package
    #   TRUE  = sign package (e.g., with a private key)
    #=========================================
    SIGN_PACKAGE = 'TRUE'

    #=========================================
    # Generate meta file after build
    #   FALSE = do not generate meta file
    #   TRUE  = generate meta file
    #=========================================
    META_FILE = 'TRUE'

    #=========================================
    # Update the index.json file after build
    #   FALSE = do not update index.json
    #   TRUE  = update and re-sign index.json with the ed25519 private key at
    #           prj/config/keys/ed25519_priv.pem
    # Use this to maintain a versioned package index for deployment.
    #=========================================
    UPDATE_INDEX = 'TRUE'
    META_URL = None  # e.g., 'https://example.com/downloads/{version}/meta.json'

    #=========================================
    # Checksum algorithm for package integrity
    #   e.g. 'sha256', 'md5', etc.
    #   WARNING: changing this requires a matching update in the client's
    #   update checker. The default 'sha256' should not be changed unless
    #   all deployed clients are updated first.
    #=========================================
    CHECKSUM_ALGO = 'sha256'

    #=========================================
    # Build as one file or one directory
    #   FALSE = one directory
    #   TRUE  = one file
    #=========================================
    ONEFILE = 'FALSE'

    #=========================================
    # PyInstaller one-folder contents directory name
    # Only used when ONEFILE = 'FALSE'
    # Empty = keep PyInstaller default
    #=========================================
    CONTENTS_DIRECTORY = '_internal'

    #=========================================
    # Show console window
    #   FALSE = no console
    #   TRUE  = show console
    #=========================================
    WINDOW = 'FALSE'

    #=========================================
    # Clean mode
    #   Clean cache and remove temp files before building
    #   FALSE = do not clean
    #   TRUE  = clean before build
    #=========================================
    CLEAN = 'TRUE'

    #=========================================
    # Confirm mode
    #   Replace dist directory without asking for confirmation
    #   FALSE = do not confirm
    #   TRUE  = confirm replace
    #=========================================
    CONFIRM = 'FALSE'

    #=========================================
    # Additional folders to include in build
    # Add folder paths as needed
    #=========================================
    FOLDERS = [
        '/assets',
    ]

    #=========================================
    # Additional files to include in build
    # Add file paths as needed
    #=========================================
    FILES = [
    ]

    #=========================================
    # Excluded modules
    # Add module names to exclude from build
    #=========================================
    EXCLUDE = [
        'PySide6.QtWebEngineCore'
    ]
