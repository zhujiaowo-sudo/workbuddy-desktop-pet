"""Build the same GUI executable used by the minimal stdin hook collector."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def fix_native_icu(dist: Path) -> None:
    """Qt 6.12 uses Windows ICU; Git's version-suffixed ICU is incompatible."""
    import pefile
    internal = dist / "_internal"
    with pefile.PE(str(internal / "PySide6/Qt6Core.dll"), max_symbol_exports=100000) as core:
        dependency = next((d for d in core.DIRECTORY_ENTRY_IMPORT if d.dll.lower() == b"icuuc.dll"), None)
    candidate = internal / "icuuc.dll"
    if dependency is None or not candidate.exists():
        return
    required = {s.name for s in dependency.imports if s.name}
    with pefile.PE(str(candidate), max_symbol_exports=100000) as pe:
        supplied = {s.name for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
    if required <= supplied:
        return
    system = Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/icuuc.dll"
    if not system.is_file():
        raise RuntimeError("Qt requires native Windows ICU; build on a supported Windows 10/11 host")
    with pefile.PE(str(system), max_symbol_exports=100000) as pe:
        native = {s.name for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
    if not required <= native:
        raise RuntimeError("Native Windows ICU does not provide the required Qt interface")
    candidate.unlink()
    # Remove the unrelated Git data library collected only with its ICU runtime.
    with pefile.PE(str(internal / "PySide6/Qt6Core.dll")) as pe:
        if any(d.dll.lower().startswith(b"icudt") for d in pe.DIRECTORY_ENTRY_IMPORT):
            raise RuntimeError("Unexpected direct ICU data dependency")
    for unused in internal.glob("icudt*.dll"):
        unused.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, default=Path("build/windows"))
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    work = args.work.absolute()
    work.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, str(project / "src"))
    from PySide6.QtWidgets import QApplication
    from workbuddy_pet.ui.pet import mascot_icon
    from workbuddy_pet import __version__
    app = QApplication.instance() or QApplication([])
    icon = work / "pet.ico"
    if not mascot_icon().pixmap(256, 256).save(str(icon), "ICO"):
        raise RuntimeError("Could not write application icon")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
                    "--name", "WorkBuddyDesktopPet", "--icon", str(icon), "--paths", str(project / "src"),
                    "--distpath", str(project / "dist"), "--workpath", str(work / "pyinstaller"),
                    "--specpath", str(work), str(project / "launch.py")], cwd=project, check=True)
    dist = project / "dist/WorkBuddyDesktopPet"
    fix_native_icu(dist)
    for source in (project / "README.md", project / "NOTICE.md", project / "docs/releasing.md"):
        if source.exists():
            shutil.copy2(source, dist / source.name)
    shutil.copytree(project / "licenses", dist / "licenses/public-licenses", dirs_exist_ok=True)
    licenses = dist / "THIRD_PARTY_LICENSES.txt"
    licenses.write_text("Qt / PySide6 / Shiboken: LGPL-3.0 / GPL / commercial license as applicable.\n"
                        "https://doc.qt.io/qtforpython-6/licenses.html\n"
                        "Python: PSF license, https://docs.python.org/3/license.html\n"
                        "PyInstaller: GPL-2.0-or-later with bootloader exception, https://pyinstaller.org/\n"
                        "This package uses dynamically linked Qt libraries in _internal; source is in the project repository.\n", encoding="utf-8")
    # Include the actual license texts shipped by the Qt wheels, when present.
    import importlib.metadata
    for package in ("PySide6_Essentials", "shiboken6"):
        metadata = importlib.metadata.distribution(package)
        for entry in metadata.files or []:
            if "license" in str(entry).lower() and str(entry).endswith((".txt", ".md", "LICENSE", "COPYING")):
                source = Path(metadata.locate_file(entry))
                if source.is_file():
                    target = dist / "licenses" / package / source.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    archive = shutil.make_archive(str(project / "dist" / f"workbuddy-desktop-pet-{__version__}-windows-x64"), "zip",
                                  root_dir=project / "dist", base_dir="WorkBuddyDesktopPet")
    sha = hashlib.file_digest(Path(archive).open("rb"), "sha256").hexdigest()
    (project / "dist/SHA256SUMS.txt").write_text(sha + "  " + Path(archive).name + "\n", encoding="utf-8")
    print(json.dumps({"archive": archive, "sha256": sha}, indent=2))


if __name__ == "__main__":
    main()
