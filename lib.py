from __future__ import annotations

import os
import stat
from configparser import ConfigParser
from dataclasses import dataclass
from hashlib import md5
from typing import List, Optional, Dict

DEFAULT_CONFIG_FILE_PATH = "~/.clean_files"


@dataclass
class DefaultActions:
    """Default actions for found files

    If set to None - user will be prompted for each file
    """
    copy: Optional[bool]  # If set to false then move instead of copying
    delete: Optional[bool]  # Duplicate, empty or temp file
    replace_old_version: Optional[bool]  # For files with the same content
    replace_new_version: Optional[bool]  # For files with the same name
    set_default_attributes: Optional[bool]
    rename: Optional[bool]  # Without problematic chars
    do_nothing: Optional[bool]  # Only display

    @classmethod
    def create(cls) -> DefaultActions:
        return cls(
            copy=None,
            delete=None,
            replace_old_version=None,
            replace_new_version=None,
            set_default_attributes=None,
            rename=None,
            do_nothing=None
        )


@dataclass
class Configuration:
    main_dir: str
    other_dirs: List[str]
    default_file_access_rights: str
    problematic_chars: List[str]
    substitute_char: str
    temp_file_suffixes: List[str]
    default_actions: DefaultActions

    @classmethod
    def create(cls, main_dir: str, other_dirs: List[str], config_path: str,
               default_actions: DefaultActions) -> Configuration:
        if not cls.is_configuration_file_accessible(config_path):
            raise ValueError(f"Cannot access configuration file: {config_path}")

        for path in (main_dir, *other_dirs):
            if not cls.is_valid_directory(path):
                raise ValueError(f"Directory {path} does not exist or has insufficient access rights")

        config = ConfigParser()
        config.read(config_path)

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
        return os.path.isdir(path) and os.access(path, os.R_OK | os.W_OK | os.X_OK)

    @staticmethod
    def is_configuration_file_accessible(path: str):
        return os.path.isfile(path) and os.access(path, os.R_OK)


@dataclass
class FileDescription:
    path: str  # Relative to root_dir
    access_rights: str
    md5_hash: str
    size: int  # Bytes

    @classmethod
    def from_path(cls, path: str) -> FileDescription:
        return cls(
            path=path,
            access_rights=cls._get_file_access_rights(path),
            md5_hash=cls._get_file_md5(path),
            size=cls._get_file_size(path)
        )

    @classmethod
    def from_directory(cls, dir_path: str) -> List[FileDescription]:
        return [
            cls.from_path(os.path.join(dir_path, file_path))
            for file_path in list_files_in_directory(dir_path)
        ]

    @staticmethod
    def _get_file_md5(path: str) -> str:
        with open(path, mode="rb") as file:
            return md5(file.read()).hexdigest()

    @staticmethod
    def _get_file_size(path: str) -> int:
        return os.path.getsize(path)

    @staticmethod
    def _get_file_access_rights(path: str) -> str:
        return stat.filemode(os.stat(path).st_mode)[1:]

    @property
    def filename(self) -> str:
        return os.path.basename(self.path)

    @property
    def extension(self) -> str:
        return os.path.splitext(self.path)[1]

    def is_empty(self) -> bool:
        return self.size == 0


def list_files_in_directory(directory: str) -> List[str]:
    """Return a list of relative paths of all files in the given directory and its subdirectories."""
    return [
        os.path.relpath(os.path.join(root, file), directory)
        for root, _, files in os.walk(directory)
        for file in files
    ]


class App:
    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.main_dir_files = FileDescription.from_directory(self.configuration.main_dir)
        self.other_dirs_files: Dict[str, List[FileDescription]] = {}

        for other_dir in configuration.other_dirs:
            self.other_dirs_files[other_dir] = FileDescription.from_directory(other_dir)

    def run(self):
        print(f"Config: {self.configuration}")
        pass
