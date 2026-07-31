from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


project_root = Path.cwd()
data_files = [
    (str(project_root / "app" / "baseline_seeds"), "app/baseline_seeds"),
    (str(project_root / "app" / "executor_skills"), "app/executor_skills"),
    (str(project_root / "app" / "integrations" / "moonshot" / "assets"), "app/integrations/moonshot/assets"),
    (str(project_root / "app" / "prompts"), "app/prompts"),
]
binaries = []
hidden_imports = []

def runtime_submodule(name: str) -> bool:
    """Exclude third-party tests, demos, notebooks, and command-line frontends."""
    parts = name.lower().split(".")
    banned = {"test", "tests", "testing", "cli", "demo", "demos", "notebook", "notebooks", "pytest_plugin"}
    return not any(
        part in banned
        or part.startswith("test_")
        or part.endswith(("_test", "_tests", "_demo"))
        for part in parts
    )


for package in (
    "moonshot",
    "aiohttp",
    "anthropic",
    "boto3",
    "botocore",
    "google.generativeai",
    "h2ogpte",
    "langchain_openai",
    "nltk",
    "openai",
    "ragas",
    "readability",
    "rouge_score",
    "together",
):
    data_files += collect_data_files(package, include_py_files=False)
    hidden_imports += collect_submodules(package, filter=runtime_submodule)

for package in ("homoglyphs", "pylcs", "slugify"):
    hidden_imports += collect_submodules(package)

for distribution in (
    "aiverify-moonshot",
    "fastapi",
    "langgraph",
    "langgraph-checkpoint-sqlite",
    "pydantic",
):
    data_files += copy_metadata(distribution, recursive=True)

analysis = Analysis(
    [str(project_root / "app" / "desktop_server.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=data_files,
    hiddenimports=sorted(set(hidden_imports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "bert_score",
        "cv2",
        "flair",
        "nudenet",
        "onnxruntime",
        "sentence_transformers",
        "spacy",
        "tensorflow",
        "textattack",
        "tkinter",
        "torch",
        "torchmetrics",
        "torchvision",
        "transformers",
    ],
    noarchive=False,
)
# The upstream NLTK PyInstaller hook scans every directory in nltk.data.path,
# including the build user's roaming profile. Desktop NLTK assets are bundled
# separately by Tauri, so reject host-specific nltk_data from the sidecar.
analysis.datas = [
    item
    for item in analysis.datas
    if not item[0].replace("\\", "/").startswith("nltk_data/")
]
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="oxo-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    contents_directory="oxo-backend-lib",
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="oxo-backend",
)
