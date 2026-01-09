import os
import stat
from pathlib import Path

import pytest

sys_path_added = False
try:
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).parent.parent))
    sys_path_added = True
except Exception:
    pass

from batch_executor import LocalCopyDelivery, SftpDelivery


def test_local_copy_clears_destination(tmp_path):
    src = tmp_path / "src.csv"
    src.write_text("data", encoding="utf-8")

    dest_dir = tmp_path / "dest"
    dest_dir.mkdir(parents=True, exist_ok=True)
    old_file = dest_dir / "old.txt"
    old_file.write_text("old", encoding="utf-8")

    delivery = LocalCopyDelivery()
    ok, err = delivery.deliver(src, dest_dir)

    assert ok
    assert err is None
    assert not old_file.exists(), "Old file should be removed"
    copied = dest_dir / src.name
    assert copied.exists(), "CSV should be copied"
    assert copied.read_text(encoding="utf-8") == "data"


class DummySFTP:
    def __init__(self):
        self.cwd = "/"
        self.files = {}  # path -> is_dir(bool)

    def chdir(self, path):
        # Simulate existing path
        if path not in self.files or not self.files[path]:
            raise IOError("no such dir")
        self.cwd = path

    def mkdir(self, path):
        self.files[path] = True

    def listdir_attr(self, path):
        class Entry:
            def __init__(self, filename, mode):
                self.filename = filename
                self.st_mode = mode

        entries = []
        for p, is_dir in self.files.items():
            if os.path.dirname(p.rstrip("/")) == path.rstrip("/"):
                filename = os.path.basename(p)
                mode = stat.S_IFDIR if is_dir else stat.S_IFREG
                entries.append(Entry(filename, mode))
        return entries

    def remove(self, path):
        if path in self.files and not self.files[path]:
            del self.files[path]

    def put(self, src, dest):
        self.files[dest] = False


def test_sftp_clears_files(monkeypatch, tmp_path):
    sftp = DummySFTP()
    delivery = SftpDelivery(host="x")  # host unused here

    # Monkeypatch transport to avoid network
    class DummyTransport:
        def __init__(self, *args, **kwargs):
            pass
        def connect(self, **kwargs):
            pass
        def close(self):
            pass
    monkeypatch.setattr("paramiko.Transport", DummyTransport, raising=False)
    monkeypatch.setattr("paramiko.SFTPClient.from_transport", lambda t: sftp, raising=False)

    # Set up remote dir with old file
    remote_dir = "/remote/input"
    sftp.files[remote_dir] = True
    sftp.files[f"{remote_dir}/old.txt"] = False

    src = tmp_path / "src.csv"
    src.write_text("data", encoding="utf-8")

    ok, err = delivery.deliver(src, remote_dir)

    assert ok
    assert err is None
    assert f"{remote_dir}/old.txt" not in sftp.files, "Old file should be removed"
    assert f"{remote_dir}/{src.name}" in sftp.files, "CSV should be uploaded"
