from __future__ import annotations

import os
from configparser import ConfigParser
from dataclasses import dataclass
from typing import List, Optional

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
    root_dir: str
    path: str  # Relative to root_dir
    access_rights: str
    md5_hash: str
    size: int  # Bytes

    @property
    def filename(self) -> str:
        pass

    @property
    def extension(self) -> str:
        pass

    def is_empty(self) -> bool:
        pass


def run(config: Configuration):
    print(f"Config: {config}")
