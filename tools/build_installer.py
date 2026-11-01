"""Build the current-user EXE installer from a verified portable payload."""
import argparse,os,shutil,subprocess,sys,hashlib
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--compiler',type=Path)
    parser.add_argument('--dist-root',type=Path,default=Path('dist'))
    parser.add_argument('--output',type=Path,default=Path('dist'))
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1];sys.path.insert(0,str(project/'src'))
    from workbuddy_pet import __version__
    compiler=args.compiler or os.environ.get('ISCC') or shutil.which('iscc')
    if not compiler:raise SystemExit('Install Inno Setup 7 and pass --compiler <ISCC.exe>')
    payload=(args.dist_root/'WorkBuddyDesktopPet').resolve()
    if not (payload/'WorkBuddyDesktopPet.exe').is_file():raise SystemExit('Build the portable application first')
    args.output.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(compiler),'/DAppVersion='+__version__,'/DPayloadDir='+str(payload),
                    '/DOutputPath='+str(args.output.resolve()),str(project/'installer/workbuddy.iss')],check=True)
    exe=args.output/f'workbuddy-desktop-pet-{__version__}-windows-x64-setup.exe'
    sums=args.output/'SHA256SUMS.txt'
    lines=sums.read_text(encoding='utf-8').splitlines() if sums.exists() else []
    lines=[line for line in lines if not line.endswith('  '+exe.name)]
    with exe.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    sums.write_text('\n'.join([*lines,digest+'  '+exe.name])+'\n',encoding='utf-8')
if __name__=='__main__':main()
