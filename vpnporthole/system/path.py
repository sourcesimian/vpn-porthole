import tempfile
import os
import shutil
import uuid


class TmpDir(object):
    __disown = False

    def __init__(self):
        dir = None
        self.__path = tempfile.mkdtemp(prefix='vpnporthole-', dir=dir)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if not self.__disown:
            if os.path.isdir(self.__path):
                shutil.rmtree(self.__path)

    def __del__(self):
        self.close()

    @property
    def path(self):
        return self.__path

    def disown(self):
        self.__disown = True


class TmpFifo(object):
    __disown = False
    __fifo = None

    def __init__(self):
        self.__tmpdir = TmpDir()
        self.__fifo = os.path.join(self.__tmpdir.path, str(uuid.uuid4())[:8])
        os.mkfifo(self.__fifo)

    @property
    def path(self):
        return self.__fifo

    def close(self):
        if not self.__disown:
            if os.path.isfile(self.__fifo):
                os.unlink(self.__fifo)

    def __del__(self):
        self.close()


def abs_path(path):
    return path
