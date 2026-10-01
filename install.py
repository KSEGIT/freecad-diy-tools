"""Install the independent DIY add-on without changing Woodworking files."""
import argparse
from pathlib import Path
import shutil


def install(mod_root):
    source = Path(__file__).resolve().parent / 'DIYWorkbenchTools'
    target = mod_root / 'DIYWorkbenchTools'
    if not (source / 'InitGui.py').is_file():
        raise RuntimeError('Missing add-on InitGui.py; use a complete checkout.')
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.is_file() and item.suffix in ('.py', '.svg', '.FCMacro'):
            shutil.copy2(item, target / item.name)
    print('Installed:', target)
    print('Save your model and restart FreeCAD, the DIY tools row will appear in every workbench.')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod-root', type=Path, default=Path.home() / 'Library/Application Support/FreeCAD/v1-1/Mod')
    install(parser.parse_args().mod_root)
