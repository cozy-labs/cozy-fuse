from multiprocessing import Process

import subprocess
import sys
import download_binary


def main():
    config = subprocess.call(['python', 'config.py', '--size=720x350'])
    if config is 0:
        download_bin = Process(target = download_binary.main)
        download_bin.start()
        download = subprocess.call(['python', 'binary.py', '--size=720x350'])
        if download is 0:
            download_bin.terminate()
            subprocess.call(['python', 'end.py', '--size=720x350'])
            sys.exit(1)


if __name__ == '__main__':
    main()
