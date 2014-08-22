import os
import subprocess

from setuptools import setup

setup_dir = os.path.dirname(os.path.abspath(__file__))

# Temporary trick to install wxpython on Debian/Ubuntu and FreeBSD
# TODO: OSX compatibility
if os.path.exists('/etc/debian_version'):
    subprocess.call('apt-get install -y -qq python-wxgtk2.8', shell=True)
else:
    proc = subprocess.Popen(['uname', '-rs'], stdout=sucprocess.PIPE)
    if proc.stdout.read()[0:10] == "FreeBSD 10":
        subprocess.call('pkg install -y py27-wxPython28', shell=True)
    else:
        print 'Cozy FUSE graphical client installation is only compatible with'\
              ' Debian based systems for now, install "wxpython 2.8" manually '\
              'on your system to make it work properly otherwise.'


setup(
    name='cozy-fuse',
    version='0.1.3',
    description='FUSE implementation for Cozy Files',
    author='Cozy Cloud',
    author_email='contact@cozycloud.cc',
    url='https://github.com/cozy/cozy-fuse',
    download_url = 'https://github.com/cozy/cozy-fuse/tarball/0.1.2',
    keywords = ['cozy', 'fuse', 'linux', 'osx'],
    license='LGPL',
    install_requires=[
        "fuse-python>=0.2",
        "CouchDB>=0.9",
        "requests>=2.0.1",
        "pyyaml",
        "argparse",
        "argcomplete",
        "lockfile",
        "python-daemon"
    ],
    setup_requires=[],
    tests_require=[
    ],
    packages=['cozyfuse', 'cozyfuse.interface' ],
    include_package_data=True,
    zip_safe=False,
    data_files=[
        ("cozyfuse/interface/icon", ("cozyfuse/interface/icon/icon.png",)),
        ("cozyfuse/interface/icon", ("cozyfuse/interface/icon/small_icon.png",)),
    ],
    entry_points={
        'console_scripts': [
            'cozy-fuse = cozyfuse.__main__:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
    ],
)

