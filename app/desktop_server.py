from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path


READY_PREFIX = "OXO_DESKTOP_READY "


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Oxo Tracker desktop API sidecar")
    parser.add_argument("--token", required=True)
    parser.add_argument("--resource-root", required=True, type=Path)
    parser.add_argument("--app-home", required=True, type=Path)
    parser.add_argument("--asset-version", default="unversioned")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--development", action="store_true")
    parser.add_argument("--moonshot-data-root", type=Path)
    args = parser.parse_args()
    if args.development and args.moonshot_data_root is None:
        parser.error("--development requires --moonshot-data-root")
    return args


def configure_environment(args: argparse.Namespace) -> None:
    app_home = args.app_home.expanduser().resolve()
    resource_root = args.resource_root.expanduser().resolve()
    moonshot_data_root = (
        args.moonshot_data_root.expanduser().resolve()
        if args.moonshot_data_root is not None
        else app_home / "data" / "moonshot-data"
    )
    values = {
        "OXO_DESKTOP_MODE": "1",
        "OXO_DESKTOP_TOKEN": args.token,
        "OXO_ASSET_VERSION": args.asset_version,
        "OXO_RESOURCE_ROOT": str(resource_root),
        "OXO_APP_HOME": str(app_home),
        "OXO_DATA_ROOT": str(app_home / "data"),
        "OXO_CONFIG_ROOT": str(app_home / "config"),
        "OXO_LOG_ROOT": str(app_home / "logs"),
        "OXO_CACHE_ROOT": str(app_home / "cache"),
        "OXO_EXPORT_ROOT": str(app_home / "exports"),
        "OXO_MOONSHOT_DATA_ROOT": str(moonshot_data_root),
        "OXO_MOONSHOT_ARCHIVE": str(resource_root / "moonshot-data.zip"),
        "HF_HOME": str(app_home / "cache" / "huggingface"),
        "HF_HUB_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }
    nltk_data = resource_root / "nltk_data"
    if nltk_data.is_dir() or not args.development:
        values["NLTK_DATA"] = str(nltk_data)
    os.environ.update(values)


def serve(args: argparse.Namespace) -> None:
    configure_environment(args)

    from app.core.paths import APP_PATHS

    if args.development:
        if not (APP_PATHS.moonshot_data_root / "datasets").is_dir():
            raise FileNotFoundError(
                "Moonshot development datasets were not found at "
                f"{APP_PATHS.moonshot_data_root}"
            )
        APP_PATHS.ensure_writable_directories()
    else:
        APP_PATHS.prepare_desktop_assets(args.asset_version)

    import uvicorn
    from app.main import app

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((args.host, 0))
    listener.listen(2048)
    port = int(listener.getsockname()[1])
    print(
        READY_PREFIX
        + json.dumps(
            {"host": args.host, "port": port, "pid": os.getpid()},
            separators=(",", ":"),
        ),
        flush=True,
    )

    config = uvicorn.Config(
        app,
        host=args.host,
        port=port,
        log_level="info",
        access_log=False,
    )
    uvicorn.Server(config).run(sockets=[listener])


def main() -> None:
    serve(parse_args())


if __name__ == "__main__":
    main()
