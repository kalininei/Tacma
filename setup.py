import sys
import os
import os.path
import shutil


# ---- Converting program options
def rm_file_and_empty_dirs(fname):
    'removes file and all empty upper directories'
    fname = os.path.abspath(fname.strip())
    if not os.path.exists(fname):
        return
    while os.path.isfile(fname) or len(os.listdir(fname)) == 0:
        try:
            print 'Removing %s' % fname
            os.remove(fname) if os.path.isfile(fname) else os.rmdir(fname)
            fname = os.path.dirname(fname)
        except Exception as e:
            print 'failed to delete %s: %s' % (fname, str(e))
            break

if len(sys.argv) == 1 or sys.argv[1] in ['-h', '-help', 'help', 'usage']:
    t = 'Setup usage:\n'
    t += '\tinstall - installs program to default directories\n'
    t += '\tuninstall - remove all installed files\n'
    t += '\tclear - clears current directory '
    t += 'from temporary assembling files\n'
    print t
    quit()


if sys.argv[1] == 'install':
    # force install --record installed_files.txt
    if '--record' not in sys.argv:
        sys.argv.append('--record')
        sys.argv.append('foo')
    ir = sys.argv.index('--record') + 1
    sys.argv[ir] = 'installed_files.txt'

# uninstall procedure
if sys.argv[1] == 'uninstall':
    try:
        f = open('installed_files.txt')
        fls = f.readlines()
        map(rm_file_and_empty_dirs, fls)
        rm_file_and_empty_dirs('installed_files.txt')
    except:
        pass
    quit()

# clear current directory
if sys.argv[1] == 'clear':
    ddir = ['dist', 'build', 'Tacma.egg-info']
    for d in ddir:
        if os.path.exists(d):
            print 'Removing %s' % os.path.abspath(d)
            if os.path.isfile(d):
                os.remove(d)
            else:
                shutil.rmtree(d)
    quit()


# ---- Preprocessing
# copy config.py into TacmaGui dir
shutil.copyfile('config.py', 'TacmaGui/config.py')
# ----


# ----- Setup Process
import config
from setuptools import setup
setup(
    name=config.progname,
    version=config.version,
    packages=['TacmaGui'],
    entry_points={
        'console_scripts': ['%s = TacmaGui.tacma:main' % config.progname]},

    package_data={
            'TacmaGui': ['misc/*.png']
    },

    author="KalininEI",
    author_email="kalininei@yandex.ru",
    description="Working activity tracker",
)
# ---------


# ---- PostProcessing
# delete config.py from TacmaGui dir
import os
os.remove('TacmaGui/config.py')
# ----
