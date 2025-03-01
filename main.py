#!/usr/bin/python3

import argparse

from lib import DEFAULT_CONFIG_FILE_PATH, Configuration, DefaultActions, run


def main():
    parser = argparse.ArgumentParser(description="Clean up files")
    parser.add_argument('main_dir', type=str, help='The main directory')
    parser.add_argument('other_dirs', type=str, nargs='+', help='Other directories')
    parser.add_argument("--config",  type=str, required=False, default=DEFAULT_CONFIG_FILE_PATH,
                        help="Path of the configuration file")

    args = parser.parse_args()

    config = Configuration.create(
        main_dir=args.main_dir,
        other_dirs=args.other_dirs,
        config_path=args.config,
        default_actions=DefaultActions.create()
    )

    run(config)


if __name__ == "__main__":
    main()
