#!/usr/bin/python3
"""
This script is designed to clean up files in a specified main directory and other directories.
It performs various file operations such as deleting empty or temporary files, handling duplicates,
renaming files with problematic characters, and moving or copying files to the main directory.

The script uses a configuration file (`clean_files.ini`) to define default actions and settings.
It can operate in both interactive and non-interactive modes based on the configuration.

Main functionalities include:
- Deleting empty files
- Deleting temporary files based on their extensions
- Handling duplicate files by content (MD5 hash) - select one to leave and delete others
- Handling files with the same name - select one to leave and delete others
- Renaming files with problematic characters in their names
- Changing file permissions to default settings
- Moving or copying files from other directories to the main directory

Usage:
    python3 main.py <main_dir> <other_dirs> [--config <config_path>]

Arguments:
    main_dir: The main directory to clean up.
    other_dirs: Other directories to include in the cleanup process.
    --config: Optional path to the configuration file (default: ./clean_files.ini).

Requirements:
    - Python 3.8+
    - No external dependencies

Author:
    Mikołaj Garbowski
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
from configparser import ConfigParser
from dataclasses import dataclass
from hashlib import md5
from typing import Optional, List, Dict, Generator, Tuple

DEFAULT_CONFIG_FILE_PATH = "./clean_files.ini"


@dataclass
class DefaultActions:
    """Default actions for found files

    If set to None - user will be prompted for each file
    Otherwise, action will be non-interactive

    Consult the 'ACTIONS' section of the clean_files.ini file for more information
    """
    copy: Optional[bool]  # If set to false then move instead of copying
    delete: Optional[bool]  # Duplicate, empty or temp file
    replace_old_version: Optional[bool]  # For files with the same content
    replace_new_version: Optional[bool]  # For files with the same name
    set_default_attributes: Optional[bool]
    rename: Optional[bool]  # Without problematic chars

    @classmethod
    def always_prompt(cls) -> DefaultActions:
        """Factory for configuration that will prompt the user for each action"""
        return cls(
            copy=None,
            delete=None,
            replace_old_version=None,
            replace_new_version=None,
            set_default_attributes=None,
            rename=None,
        )

    @classmethod
    def from_config(cls, config: ConfigParser) -> DefaultActions:
        """Factory for parsing configuration loaded from .ini file"""
        return cls(
            copy=cls._parse_optional_flag(config.get("ACTIONS", "copy")),
            delete=cls._parse_optional_flag(config.get("ACTIONS", "delete")),
            replace_old_version=cls._parse_optional_flag(config.get("ACTIONS", "replace_old_version")),
            replace_new_version=cls._parse_optional_flag(config.get("ACTIONS", "replace_new_version")),
            set_default_attributes=cls._parse_optional_flag(config.get("ACTIONS", "set_default_attributes")),
            rename=cls._parse_optional_flag(config.get("ACTIONS", "rename")),
        )

    @staticmethod
    def _parse_optional_flag(flag: str) -> Optional[bool]:
        if flag == "True":
            return True
        elif flag == "False":
            return False
        elif flag == "None":
            return None

        raise ValueError("Expected 'True', 'False' or 'None'")


@dataclass
class Configuration:
    """Configuration for the execution of the script"""
    main_dir: str
    other_dirs: List[str]
    default_file_access_rights: str
    problematic_chars: List[str]
    substitute_char: str
    temp_file_suffixes: List[str]
    default_actions: DefaultActions

    @classmethod
    def create(cls, main_dir: str, other_dirs: List[str], config_path: str) -> Configuration:
        """Factory for creating Configuration based on .ini file and list of directories"""
        if not cls.is_configuration_file_accessible(config_path):
            raise ValueError(f"Cannot access configuration file: {config_path}")

        for path in (main_dir, *other_dirs):
            if not cls.is_valid_directory(path):
                raise ValueError(f"Directory {path} does not exist or has insufficient access rights")

        config = ConfigParser()
        config.read(config_path)

        default_actions = DefaultActions.from_config(config)

        return cls(
            main_dir=main_dir,
            other_dirs=other_dirs,
            default_file_access_rights=config['DEFAULT']['default_file_access_rights'],
            problematic_chars=list(config['DEFAULT']['problematic_chars']),
            substitute_char=config['DEFAULT']['substitute_char'],
            temp_file_suffixes=config['DEFAULT']['temp_file_suffixes'].split(', '),
            default_actions=default_actions,
        )

    @staticmethod
    def is_valid_directory(path: str):
        """Checks if path is a directory and is accessible"""
        return os.path.isdir(path) and os.access(path, os.R_OK | os.W_OK | os.X_OK)

    @staticmethod
    def is_configuration_file_accessible(path: str):
        """Checks if path is a readable file"""
        return os.path.isfile(path) and os.access(path, os.R_OK)


@dataclass
class FileDescription:
    """Representation of a file in the filesystem"""
    path: str  # Relative
    access_rights: str
    md5_hash: str
    size: int  # Bytes
    modification_timestamp: float

    @classmethod
    def from_path(cls, path: str) -> FileDescription:
        """Factory, loads information from the filesystem"""
        return cls(
            path=path,
            access_rights=cls._get_file_access_rights(path),
            md5_hash=cls._get_file_md5(path),
            size=cls._get_file_size(path),
            modification_timestamp=cls._get_modification_time(path)
        )

    @classmethod
    def from_directory(cls, dir_path: str) -> List[FileDescription]:
        """Factory, creates instances for all files in a given directory"""
        return [
            cls.from_path(os.path.join(dir_path, file_path))
            for file_path in list_files_in_directory(dir_path)
        ]

    @staticmethod
    def _get_file_md5(path: str) -> str:
        """MD5 hash of the file contents for speeding up comparing large files"""
        with open(path, mode="rb") as file:
            return md5(file.read()).hexdigest()

    @staticmethod
    def _get_file_size(path: str) -> int:
        """Read file size in bytes from the filesystem"""
        return os.path.getsize(path)

    @staticmethod
    def _get_file_access_rights(path: str) -> str:
        """Read file permissions from the filesystem as rwxrwxrwx string"""
        return stat.filemode(os.stat(path).st_mode)[1:]

    @staticmethod
    def _get_modification_time(path: str) -> float:
        """Read modification timestamp from the filesystem"""
        return os.stat(path).st_mtime

    @property
    def filename(self) -> str:
        """Extract filename from the path"""
        return os.path.basename(self.path)

    @property
    def extension(self) -> str:
        """Extract extension from the path (includes the dot)"""
        return os.path.splitext(self.path)[1]

    def is_empty(self) -> bool:
        """Size in bytes equal to 0"""
        return self.size == 0


def list_files_in_directory(directory: str) -> List[str]:
    """Return a list of relative paths of all files in the given directory and its subdirectories"""
    return [
        os.path.relpath(os.path.join(root, file), directory)
        for root, _, files in os.walk(directory)
        for file in files
    ]


def get_input(prompt: str, options: List[str]) -> str:
    """Make the user select one of the displayed options"""
    options = f"[{'/'.join(options)}]"

    while True:
        choice = input(f"{prompt}: {options}").strip()
        if choice in options:
            return choice

        print(f"Select one of: {options}")


def permission_string_to_numeric(permissions: str) -> int:
    """Convert permissions string ('rwxr-xr-x') to numeric format
    https://stackoverflow.com/a/57415662

    >>> mask = permission_string_to_numeric("rwxr-xr-x")
    >>> oct(mask)
    '0o755'
    """
    assert len(permissions) == 9, 'Bad permission length'
    assert all(permissions[k] in 'rw-' for k in [0, 1, 3, 4, 6, 7]), 'Bad permission format (read-write)'
    assert all(permissions[k] in 'xs-' for k in [2, 5]), 'Bad permission format (execute)'
    assert permissions[8] in 'xt-', 'Bad permission format (execute other)'

    mask = 0

    if permissions[0] == 'r': mask |= stat.S_IRUSR
    if permissions[1] == 'w': mask |= stat.S_IWUSR
    if permissions[2] == 'x': mask |= stat.S_IXUSR
    if permissions[2] == 's': mask |= stat.S_IXUSR | stat.S_ISUID

    if permissions[3] == 'r': mask |= stat.S_IRGRP
    if permissions[4] == 'w': mask |= stat.S_IWGRP
    if permissions[5] == 'x': mask |= stat.S_IXGRP
    if permissions[5] == 's': mask |= stat.S_IXGRP | stat.S_ISGID

    if permissions[6] == 'r': mask |= stat.S_IROTH
    if permissions[7] == 'w': mask |= stat.S_IWOTH
    if permissions[8] == 'x': mask |= stat.S_IXOTH
    if permissions[8] == 't': mask |= stat.S_IXOTH | stat.S_ISVTX

    return mask


class App:
    """Main class of the application, handles various file operations

    Consult the module doc comment for more details
    """

    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.main_dir_files: List[FileDescription] = FileDescription.from_directory(self.configuration.main_dir)
        self.other_dirs_files: Dict[str, List[FileDescription]] = {}

        self.load_file_info()

    def load_file_info(self):
        """Load current information about all the files in main and other directories from the filesystem"""
        self.main_dir_files = FileDescription.from_directory(self.configuration.main_dir)

        for other_dir in self.configuration.other_dirs:
            self.other_dirs_files[other_dir] = FileDescription.from_directory(other_dir)

    def all_files(self) -> Generator[FileDescription]:
        """Generator for all files (main and other directories)"""
        for file_description in self.main_dir_files:
            yield file_description

        for directory in self.configuration.other_dirs:
            for file_description in self.other_dirs_files[directory]:
                yield file_description

    def all_other_files(self) -> Generator[Tuple[str, FileDescription]]:
        """Generator for all files in other dirs"""
        for directory in self.configuration.other_dirs:
            for file_description in self.other_dirs_files[directory]:
                yield directory, file_description

    def list_all_files(self):
        """Display a list of all files (main and other directories)"""
        for file in self.all_files():
            print(file.path)

    def run(self):
        """Execute the main operations of the script"""
        self.list_all_files()

        self.handle_delete_empty_files()
        self.handle_delete_temporary_files()
        self.handle_duplicates()
        self.handle_same_names()
        self.handle_non_standard_permissions()
        self.handle_problematic_names()
        self.handle_move_all_files_to_main_dir()

        self.list_all_files()

    def handle_problematic_names(self):
        """Find files with names containing problematic characters and suggest renaming them

        Problematic characters and the substitute are defined in Configuration
        Interactive or non-interactive as per DefaultActions configuration
        """
        print("Looking for files with problematic names")
        for file in self.all_files():
            if self.is_name_problematic(file.filename):
                self.handle_rename(file)
        self.load_file_info()

    def handle_non_standard_permissions(self):
        """Find files with non-standard permissions and suggest changing them to the defaults

        Default permissions are defined in Configuration
        Interactive or non-interactive as per DefaultActions configuration
        """
        print("Looking for files with non-standard permissions")

        for file in self.all_files():
            if file.access_rights != self.configuration.default_file_access_rights:
                self.handle_change_access_rights(file)

        self.load_file_info()

    def handle_delete_temporary_files(self):
        """Find temporary files and suggest deleting them

        Files are considered temporary based on their extension (or suffix) as defined in Configuration
        Interactive or non-interactive as per DefaultActions configuration
        """
        print("Looking for temporary files to delete")
        for file in self.all_files():
            if self.is_temp_file(file):
                self.handle_delete(file)
        self.load_file_info()

    def handle_delete_empty_files(self):
        """Find empty files and suggest deleting them

        Interactive or non-interactive as per DefaultActions configuration
        """
        print("Looking for empty files to delete")
        for file in self.all_files():
            if file.is_empty():
                self.handle_delete(file)
        self.load_file_info()

    def handle_delete(self, file: FileDescription):
        """Handle deleting a single file, interactive or non-interactive as per DefaultActions configuration"""
        should_delete = self.configuration.default_actions.delete

        if should_delete is None:
            should_delete = get_input(f"{file.path} Delete file?", ["Y", "n"]) == "Y"

        if should_delete:
            os.remove(file.path)
            print(f"Deleted file: {file.path}")
        else:
            print(f"Skipping file: {file.path}")

    def handle_change_access_rights(self, file: FileDescription):
        """Handle modifying permissions (chmod) of a single file, interactive or non-interactive as per configuration"""
        should_change = self.configuration.default_actions.set_default_attributes
        defaults = self.configuration.default_file_access_rights

        if should_change is None:
            should_change = get_input(
                f"{file.path} File has {file.access_rights}, change to {defaults}?",
                ["Y", "n"]
            ) == "Y"

        if should_change:
            permission_mask = permission_string_to_numeric(defaults)
            os.chmod(file.path, permission_mask)
            print(f"Changed access rights for file: {file.path}")
        else:
            print(f"Skipping file: {file.path}")

    def is_temp_file(self, file: FileDescription):
        """Files are considered temporary based on filename suffix (list defined in configuration)"""
        return any(
            file.filename.endswith(extension)
            for extension in self.configuration.temp_file_suffixes
        )

    def get_all_files_by_hash(self, md5_hash: str) -> List[FileDescription]:
        """List of all files (main and other dirs) whose content matches given hash"""
        return [
            file
            for file in self.all_files()
            if file.md5_hash == md5_hash
        ]

    def get_all_files_by_name(self, name: str) -> List[FileDescription]:
        """List of all files (main and other dirs) with given filename"""
        return [
            file
            for file in self.all_files()
            if file.filename == name
        ]

    @staticmethod
    def _select_file_to_leave(files: List[FileDescription]):
        """Prompt the user to select one file from the list to leave, the rest will be deleted"""
        choice = int(get_input(
            "Which do you want to leave?",
            [str(idx) for idx in range(len(files))]
        ))
        print(f"Leaving file {files[choice].path}")
        files.pop(choice)

        for file in files:
            os.remove(file.path)
            print(f"Deleted {file.path}")

    def handle_duplicates(self):
        """Find duplicate files and select one of them to leave, deleting others

        Suggest leaving the oldest copy (assumed original)
        Files are considered duplicates if md5 hashes of their content are equal
        Interactive or non-interactive as per DefaultActions configuration
        """
        print("Looking for duplicate files (same content)")
        already_handled_hashes = set()

        for file in self.all_files():
            if file.md5_hash in already_handled_hashes:
                continue

            already_handled_hashes.add(file.md5_hash)

            copies = self.get_all_files_by_hash(file.md5_hash)
            copies.sort(key=lambda f: f.modification_timestamp)

            if len(copies) == 1:
                continue

            if self.configuration.default_actions.replace_old_version:
                print(f"Leaving file {copies[0].path}")
                for copy in copies[1:]:
                    os.remove(copy.path)
                    print(f"Deleted {copy.path}")

                continue

            print("Found duplicate files")
            for idx, file_copy in enumerate(copies):
                print(f"[{idx}] {file_copy.path}{' --- oldest copy' if idx == 0 else ''}")

            self._select_file_to_leave(copies)

        self.load_file_info()

    def handle_same_names(self):
        """Find files with the same names and select one of them to leave, deleting others

        Suggest leaving the most recently modified (assumed newest version)
        Interactive or non-interactive as per DefaultActions configuration
        """
        print("Looking for files with the same name")
        already_handled_names = set()

        for file in self.all_files():
            if file.filename in already_handled_names:
                continue

            already_handled_names.add(file.filename)

            copies = self.get_all_files_by_name(file.filename)
            copies.sort(key=lambda f: f.modification_timestamp, reverse=True)

            if len(copies) == 1:
                continue

            if self.configuration.default_actions.replace_new_version:
                print(f"Leaving file {copies[0].path}")
                for copy in copies[1:]:
                    os.remove(copy.path)
                    print(f"Deleted {copy.path}")

                continue

            print("Found files with the same name")
            for idx, file_copy in enumerate(copies):
                print(f"[{idx}] {file_copy.path}{' --- most recently modified' if idx == 0 else ''}")

            self._select_file_to_leave(copies)

        self.load_file_info()

    def is_name_problematic(self, filename: str) -> bool:
        """Does filename contain problematic characters"""
        return any(
            problematic_char in filename
            for problematic_char in self.configuration.problematic_chars
        )

    def clean_filename(self, filename: str) -> str:
        """Return a filename with problematic chars replaced with a substitute char"""
        for char in self.configuration.problematic_chars:
            filename = filename.replace(char, self.configuration.substitute_char)

        return filename

    def handle_rename(self, file: FileDescription):
        """Handle renaming a single file to remove problematic characters

        Interactive or non-interactive as per DefaultActions configuration
        """
        new_name = self.clean_filename(file.filename)

        should_rename = self.configuration.default_actions.rename
        if should_rename is None:
            should_rename = get_input(f"Rename file {file.path} to {new_name}?", ["Y", "n"]) == "Y"

        if should_rename:
            directory, _ = os.path.split(file.path)
            new_path = os.path.join(directory, new_name)
            os.rename(file.path, new_path)
            print(f"Renamed {file.path} to {new_path}")
        else:
            print(f"Skipping file {file.path}")

    def handle_move_all_files_to_main_dir(self):
        """Move or copy all files from other directories to the main directory

        Interactive or non-interactive as per DefaultActions configuration
        """
        print(f"Moving all files to the main directory {self.configuration.main_dir}")

        for other_dir, file in self.all_other_files():
            new_path = file.path.replace(other_dir, self.configuration.main_dir)

            os.makedirs(os.path.dirname(new_path), exist_ok=True)  # mkdir -p before moving a deeply nested file

            should_copy = self.configuration.default_actions.copy
            if should_copy is None:
                should_copy = get_input(f"Move or copy {file.path}?", ["m", "c"]) == "c"

            if should_copy:
                shutil.copy(file.path, new_path)
                print(f"Copied {file.path} to {new_path}")
            else:
                shutil.move(file.path, new_path)
                print(f"Moved {file.path} to {new_path}")

        self.load_file_info()


def main():
    parser = argparse.ArgumentParser(description="Clean up files")
    parser.add_argument('main_dir', type=str, help='The main directory')
    parser.add_argument('other_dirs', type=str, nargs='+', help='Other directories')
    parser.add_argument("--config", type=str, required=False, default=DEFAULT_CONFIG_FILE_PATH,
                        help="Path of the configuration file")

    args = parser.parse_args()

    config = Configuration.create(
        main_dir=args.main_dir,
        other_dirs=args.other_dirs,
        config_path=args.config,
    )

    app = App(config)
    app.run()


if __name__ == "__main__":
    main()
