import os

from setuptools import setup

# Copy cozy-fuse init script in Debian/Ubuntu
# TODO: Do the same for OSX ?
if os.path.exists('/etc/debian_version'):
    data_files = [('/etc/init.d', ['scripts/init/cozy-fuse'])]
else:
    data_files = []

setup(
    name='cozy-fuse',
    version='0.1.1',
    description='FUSE implementation for Cozy Files',
    author='Cozy Cloud',
    author_email='contact@cozycloud.cc',
    url='https://github.com/cozy/cozy-fuse-linux',
    download_url = 'https://github.com/cozy/cozy-fuse-linux/tarball/0.1.1',
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
    packages=['cozyfuse'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'cozy-fuse = cozyfuse.__main__:main',
        ],
    },
    data_files = data_files,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: LGPL',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2.8',
        'Programming Language :: Python :: 2.9',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
    ],
)

