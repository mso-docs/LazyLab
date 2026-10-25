"""Optional rootless Bubblewrap isolation, with an explicit restricted fallback."""
from functools import lru_cache
from pathlib import Path
import shutil
import subprocess
import sys


@lru_cache(maxsize=1)
def isolation_status():
    binary=shutil.which('bwrap')
    if not binary:
        return {'available':False,'reason':'Bubblewrap is not installed'}
    try:
        probe=subprocess.run([binary,'--unshare-all','--die-with-parent','--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--','/usr/bin/true'],capture_output=True,text=True,timeout=5)
        if probe.returncode:
            return {'available':False,'reason':probe.stderr.strip()[:400] or 'User namespaces unavailable'}
        return {'available':True,'reason':'Rootless Bubblewrap namespaces available','binary':binary}
    except (OSError,subprocess.SubprocessError) as exc:
        return {'available':False,'reason':str(exc)}


def command(directory:Path, mode:str):
    plain=[sys.executable,'-m','slothlab.experiments.worker']
    if mode not in {'auto','subprocess','bubblewrap'}:
        raise ValueError('Unknown execution isolation policy')
    status=isolation_status() if mode!='subprocess' else {'available':False,'reason':'Restricted subprocess explicitly selected'}
    if not status['available']:
        if mode=='bubblewrap':
            raise RuntimeError('Required Bubblewrap isolation unavailable: '+status['reason'])
        return plain, {'backend':'restricted subprocess','os_filesystem_isolation':False,'os_network_isolation':False,'fallback_reason':status['reason']}
    # Bind only runtime libraries, virtualenv and application package. The home
    # directory, credentials, datasets outside this experiment and host /tmp are absent.
    root=Path(__file__).resolve().parents[2]
    args=[status['binary'],'--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL','--ro-bind','/usr','/usr']
    for name in ('/lib','/lib64'):
        if Path(name).exists():
            args+=['--ro-bind',name,name]
    args+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/etc']
    if Path('/etc/ld.so.cache').exists():
        args+=['--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache']
    prefix=Path(sys.prefix).resolve()
    if not str(prefix).startswith('/usr/'):
        args+=['--ro-bind',str(prefix),str(prefix)]
    args+=['--ro-bind',str(root/'slothlab'),str(root/'slothlab'),
           '--bind',str(directory),'/work','--chdir','/work',
           '--setenv','PYTHONPATH',str(root),'--',*plain]
    return args, {'backend':'bubblewrap','os_filesystem_isolation':True,'os_network_isolation':True,'fallback_reason':None}
