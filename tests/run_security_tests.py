import os, sys, tempfile, shutil

sys.path.insert(0, '.')

from knowledge.version_manager import _sanitize_filename, _validate_path, VersionManager
from knowledge.text_splitter import SOPTextSplitter

tmpdir = tempfile.mkdtemp()
try:
    mgr = VersionManager(base_path=tmpdir)
    m = mgr.save_version('test.txt', 'hello')
    assert mgr.get_current('test.txt') == 'hello'
    print('PASS: VersionManager save/get')

    r = _sanitize_filename('../../etc/passwd')
    assert '..' not in r and '/' not in r
    print('PASS: path traversal sanitized')

    s = SOPTextSplitter(chunk_size=10)
    assert s.chunk_size == 50
    print('PASS: min chunk size enforced')

    base = tempfile.gettempdir()
    try:
        _validate_path(base, os.path.join(base, '..', '..', 'etc', 'passwd'))
        assert False
    except ValueError:
        print('PASS: path traversal attack blocked')

    print('ALL TESTS PASSED')
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
