"""Entry point for the acq400_cli package"""

import importlib
import logging
import pkgutil
import sys

from acq400_cli.parser import CustomParser

APPS_PATH = "acq400_cli.apps"




def main():
    parser = CustomParser(
        description="ACQ400 Command Line Interface",
        prog="acq400_cli",
        add_help=False,
    )
    parser.add_argument("app", nargs="?", help="app to run")
    args, remaining = parser.parse_known_args()

    if not args.app:
        parser.print_help()
        print()
        print_apps()
        return

    run_app(args.app, remaining)

def load_app(app_name):
    """Load an app by name"""
    try:
        app = importlib.import_module(f"{APPS_PATH}.{app_name}")
        if hasattr(app, "get_parser") and hasattr(app, "main"): return app
        logging.error(f"Invalid app '{app_name}'")
    except ModuleNotFoundError: logging.error(f"Unknown app '{app_name}'")
    sys.exit(1)

def run_app(appname, remaining):
    """Run an app by name"""
    app = load_app(appname)
    parser = app.get_parser()
    parser.prog = f"acq400_cli {appname}"
    args = parser.parse_args(remaining)
    app.main(args)

def print_apps():
    """print avalible apps and descriptions"""
    apps = importlib.import_module(APPS_PATH)
    name_max = 0
    app_descs = []
    for _, app_name, _ in sorted(pkgutil.iter_modules(apps.__path__)):
        if len(app_name) > name_max: name_max = len(app_name)
        app = importlib.import_module(f"{APPS_PATH}.{app_name}")
        desc = app.__doc__.strip().split('\n')[0]
        app_descs.append((app_name, desc))

    print("apps:")
    for name, desc in app_descs:
        print(f"  {name:<{name_max}}  {desc}")

if __name__ == "__main__":
    main()