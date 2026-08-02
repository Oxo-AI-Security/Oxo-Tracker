from __future__ import annotations

import json
import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final


SOURCE_ROOT: Final = Path(__file__).resolve().parents[2]
UTF8_BOM: Final = b"\xef\xbb\xbf"
UNSUPPORTED_DESKTOP_RECIPE_IDS: Final = frozenset(
    {
        "challenging-toxicity-prompts-completion",
        "genderbias-text2image-prompts",
        "i2p-text2image-prompts",
        "real-toxicity-prompts-completion",
        "sg-legal-glossary",
        "sg-university-tutorial-questions-legal",
    }
)


def _environment_path(name: str, default: Path) -> Path:
    raw = os.getenv(name, "").strip()
    return Path(raw).expanduser().resolve() if raw else default.resolve()


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Runtime locations shared by the web and packaged desktop builds.

    With no desktop environment variables this resolves to the repository paths
    used by the existing development workflow. The Tauri host supplies explicit
    locations before the sidecar imports the application.
    """

    source_root: Path
    resource_root: Path
    app_home: Path
    data_root: Path
    config_root: Path
    log_root: Path
    cache_root: Path
    export_root: Path
    moonshot_data_root: Path
    moonshot_archive: Path
    desktop_mode: bool

    @classmethod
    def from_environment(cls) -> "AppPaths":
        source_root = SOURCE_ROOT.resolve()
        resource_root = _environment_path("OXO_RESOURCE_ROOT", source_root)
        app_home = _environment_path("OXO_APP_HOME", source_root)
        data_root = _environment_path("OXO_DATA_ROOT", app_home / "data")
        return cls(
            source_root=source_root,
            resource_root=resource_root,
            app_home=app_home,
            data_root=data_root,
            config_root=_environment_path("OXO_CONFIG_ROOT", app_home / "config"),
            log_root=_environment_path("OXO_LOG_ROOT", app_home / "logs"),
            cache_root=_environment_path("OXO_CACHE_ROOT", app_home / "cache"),
            export_root=_environment_path("OXO_EXPORT_ROOT", app_home / "exports"),
            moonshot_data_root=_environment_path(
                "OXO_MOONSHOT_DATA_ROOT",
                data_root / "moonshot-data",
            ),
            moonshot_archive=_environment_path(
                "OXO_MOONSHOT_ARCHIVE",
                resource_root / "moonshot-data.zip",
            ),
            desktop_mode=os.getenv("OXO_DESKTOP_MODE", "").strip() == "1",
        )

    def ensure_writable_directories(self) -> None:
        for path in (
            self.app_home,
            self.data_root,
            self.config_root,
            self.log_root,
            self.cache_root,
            self.export_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def prepare_desktop_assets(self, asset_version: str = "unversioned") -> None:
        """Materialize and safely migrate Moonshot assets without losing user data."""

        if not self.desktop_mode:
            return
        self.ensure_writable_directories()
        self.moonshot_data_root.mkdir(parents=True, exist_ok=True)
        marker = self.moonshot_data_root / ".oxo-desktop-assets.json"
        if _marker_version(marker) == asset_version:
            return

        if self.moonshot_archive.is_file():
            _extract_missing(self.moonshot_archive, self.moonshot_data_root)
        else:
            seed_dir_raw = os.getenv("OXO_MOONSHOT_SEED_DIR", "").strip()
            seed_dir = Path(seed_dir_raw).expanduser().resolve() if seed_dir_raw else None
            if seed_dir and seed_dir.is_dir() and seed_dir != self.moonshot_data_root:
                _copy_missing(seed_dir, self.moonshot_data_root)
            elif not any(self.moonshot_data_root.iterdir()):
                raise FileNotFoundError(
                    f"Bundled Moonshot archive was not found: {self.moonshot_archive}"
                )

        _repair_desktop_json_assets(self.moonshot_data_root)
        marker.write_text(
            json.dumps({"assetVersion": asset_version}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _marker_version(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(payload.get("assetVersion") or "")


def _safe_archive_target(root: Path, member_name: str) -> Path:
    target = (root / member_name).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"Unsafe Moonshot archive member: {member_name}") from error
    return target


def _extract_missing(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = _safe_archive_target(destination, member.filename)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def _copy_missing(source: Path, destination: Path) -> None:
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _repair_desktop_json_assets(root: Path) -> None:
    """Apply semantic-preserving repairs needed by older desktop archives."""

    # Windows PowerShell 5.1 wrote the v0.2.0 endpoint files with a UTF-8 BOM,
    # while Moonshot's JSON loader expects plain UTF-8. Removing only those
    # three marker bytes preserves every user value, including custom endpoints.
    for json_path in root.rglob("*.json"):
        with json_path.open("rb") as json_file:
            if json_file.read(len(UTF8_BOM)) != UTF8_BOM:
                continue
            payload_without_bom = json_file.read()
        _atomic_write_bytes(json_path, payload_without_bom)

    recipes_root = root / "recipes"
    cookbooks_root = root / "cookbooks"
    if not cookbooks_root.is_dir():
        return

    for cookbook_path in cookbooks_root.glob("*.json"):
        try:
            cookbook = json.loads(cookbook_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        recipe_ids = cookbook.get("recipes")
        if not isinstance(recipe_ids, list):
            continue
        filtered_recipe_ids = [
            recipe_id
            for recipe_id in recipe_ids
            if not (
                recipe_id in UNSUPPORTED_DESKTOP_RECIPE_IDS
                and not (recipes_root / f"{recipe_id}.json").is_file()
            )
        ]
        if filtered_recipe_ids == recipe_ids:
            continue
        cookbook["recipes"] = filtered_recipe_ids
        _atomic_write_bytes(
            cookbook_path,
            (
                json.dumps(cookbook, ensure_ascii=False, indent=2)
                + "\n"
            ).encode("utf-8"),
        )


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.oxo-update")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


APP_PATHS: Final = AppPaths.from_environment()
PROJECT_ROOT: Final = APP_PATHS.source_root
RESOURCE_ROOT: Final = APP_PATHS.resource_root
APP_HOME: Final = APP_PATHS.app_home
DATA_ROOT: Final = APP_PATHS.data_root
CONFIG_ROOT: Final = APP_PATHS.config_root
LOG_ROOT: Final = APP_PATHS.log_root
CACHE_ROOT: Final = APP_PATHS.cache_root
EXPORT_ROOT: Final = APP_PATHS.export_root
MOONSHOT_DATA_ROOT: Final = APP_PATHS.moonshot_data_root
