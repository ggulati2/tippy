# PyInstaller recipe for the Tippy standalone apps.  Build it with:  scripts/build_mac.sh (Mac)  or  windows/build.bat (Windows).
# PyInstaller cannot build for another system: the Mac app is built on a Mac, the Windows app on Windows (in CI: windows-app.yml).
#
# The app is a normal folder of files (inside Tippy.app on the Mac, dist\Tippy on Windows): a copy of Python, Tippy's libraries, and Tippy's own
# frontend/ and content/ folders. Nothing needs to be installed on the Mac. The family's data is NOT in the
# app; it goes to ~/Library/Application Support/Tippy (see backend/config.py), so updating the app keeps it.
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
VERSION = (ROOT / "VERSION").read_text().strip()

analysis = Analysis(
    [str(ROOT / "scripts" / "launch.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "frontend"), "frontend"), (str(ROOT / "content"), "content"), (str(ROOT / "VERSION"), ".")],
    # uvicorn picks these by name at run time, so PyInstaller cannot see them by reading the code.
    hiddenimports=["backend.app", "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.loops.asyncio",
                   "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
                   "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"],
    excludes=["tkinter", "pytest", "unittest.mock"],
)
archive = PYZ(analysis.pure)
# console=False: no black terminal window behind the app.
executable = EXE(archive, analysis.scripts, [], exclude_binaries=True, name="Tippy", console=False,
                 icon=str(ROOT / "windows" / "Tippy.ico") if sys.platform == "win32" else None)
collected = COLLECT(executable, analysis.binaries, analysis.datas, name="Tippy")
if sys.platform == "darwin":
  app = BUNDLE(
      collected,
      name="Tippy.app",
      icon=str(ROOT / "packaging" / "Tippy.icns"),
      bundle_identifier="com.ggulati.tippy",
      version=VERSION,
      info_plist={
          "CFBundleName": "Tippy",
          "CFBundleDisplayName": "Tippy",
          "CFBundleShortVersionString": VERSION,
          "NSHighResolutionCapable": True,
          "LSMinimumSystemVersion": "10.15",
          "LSApplicationCategoryType": "public.app-category.education",
      },
  )
