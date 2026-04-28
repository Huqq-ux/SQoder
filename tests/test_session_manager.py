import sys
import os
import json
import shutil
import tempfile

_project_root = os.path.join(os.path.dirname(__file__), "..", "..")
_project_root = os.path.normpath(_project_root)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _make_temp_dir():
    return tempfile.mkdtemp(prefix="test_sessions_")


def test_create_session():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s = mgr.create_session()
        assert s["session_id"].startswith("sess_"), f"Bad id: {s['session_id']}"
        assert s["title"] == "新会话"
        assert s["message_count"] == 0
        print("PASS: create_session")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_create_session_with_title():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s = mgr.create_session(title="测试标题")
        assert s["title"] == "测试标题"
        print("PASS: create_session with title")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_list_sessions():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        mgr.create_session(title="会话1")
        mgr.create_session(title="会话2")
        sessions = mgr.list_sessions()
        assert len(sessions) == 2, f"Expected 2, got {len(sessions)}"
        print("PASS: list_sessions")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_list_sessions_sorted_by_updated():
    from Coder.tools.session_manager import SessionManager
    import time
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s1 = mgr.create_session(title="旧会话")
        time.sleep(0.1)
        s2 = mgr.create_session(title="新会话")
        sessions = mgr.list_sessions()
        assert sessions[0]["session_id"] == s2["session_id"], "Should sort by updated_at desc"
        print("PASS: list_sessions sorted by updated_at")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_get_session():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s = mgr.create_session(title="目标会话")
        found = mgr.get_session(s["session_id"])
        assert found is not None
        assert found["title"] == "目标会话"
        not_found = mgr.get_session("nonexistent")
        assert not_found is None
        print("PASS: get_session")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_update_session():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s = mgr.create_session()
        mgr.update_session(s["session_id"], {"title": "更新后标题", "message_count": 5})
        updated = mgr.get_session(s["session_id"])
        assert updated["title"] == "更新后标题"
        assert updated["message_count"] == 5
        print("PASS: update_session")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_delete_session():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s = mgr.create_session(title="待删除")
        assert len(mgr.list_sessions()) == 1
        result = mgr.delete_session(s["session_id"])
        assert result is True
        assert len(mgr.list_sessions()) == 0
        result2 = mgr.delete_session("nonexistent")
        assert result2 is False
        print("PASS: delete_session")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_delete_session_removes_directory():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s = mgr.create_session()
        sess_dir = os.path.join(tmp, s["session_id"])
        os.makedirs(sess_dir, exist_ok=True)
        with open(os.path.join(sess_dir, "test.json"), "w") as f:
            f.write("{}")
        mgr.delete_session(s["session_id"])
        assert not os.path.exists(sess_dir), "Directory should be removed"
        print("PASS: delete_session removes directory")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_update_session_from_messages():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s = mgr.create_session()
        messages = [
            {"role": "user", "content": "湘潭明天天气怎么样"},
            {"role": "assistant", "content": "湘潭明天晴，25-32度"},
        ]
        mgr.update_session_from_messages(s["session_id"], messages)
        updated = mgr.get_session(s["session_id"])
        assert "湘潭" in updated["title"], f"Title should contain 湘潭: {updated['title']}"
        assert updated["message_count"] == 2
        assert "湘潭" in updated["preview"]
        print("PASS: update_session_from_messages")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_update_session_from_messages_long_title():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s = mgr.create_session()
        long_msg = "这是一个非常非常非常非常非常非常非常非常非常非常非常长的问题标题"
        messages = [{"role": "user", "content": long_msg}]
        mgr.update_session_from_messages(s["session_id"], messages)
        updated = mgr.get_session(s["session_id"])
        assert len(updated["title"]) <= 33, f"Title too long: {updated['title']}"
        assert "..." in updated["title"]
        print("PASS: update_session_from_messages long title truncation")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_update_session_preserves_existing_title():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s = mgr.create_session(title="自定义标题")
        messages = [{"role": "user", "content": "新问题"}]
        mgr.update_session_from_messages(s["session_id"], messages)
        updated = mgr.get_session(s["session_id"])
        assert updated["title"] == "自定义标题", "Should not overwrite custom title"
        print("PASS: update_session preserves existing title")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_migrate_legacy_session():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        old_dir = os.path.join(tmp, "streamlit")
        os.makedirs(old_dir, exist_ok=True)
        with open(os.path.join(old_dir, "test.json"), "w") as f:
            f.write("{}")
        result = mgr.migrate_legacy_session("streamlit")
        assert result is not None
        assert result["session_id"] == "streamlit"
        sessions = mgr.list_sessions()
        assert any(s["session_id"] == "streamlit" for s in sessions)
        result2 = mgr.migrate_legacy_session("streamlit")
        assert len(mgr.list_sessions()) == 1, "Should not duplicate"
        print("PASS: migrate_legacy_session")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_migrate_legacy_no_directory():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        result = mgr.migrate_legacy_session("nonexistent")
        assert result is None
        print("PASS: migrate_legacy_session no directory")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_sessions_file_corruption():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        with open(mgr.sessions_file, "w") as f:
            f.write("not valid json{{{")
        sessions = mgr.list_sessions()
        assert sessions == [], "Should return empty list on corruption"
        print("PASS: sessions file corruption handling")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_empty_messages_update():
    from Coder.tools.session_manager import SessionManager
    tmp = _make_temp_dir()
    try:
        mgr = SessionManager(base_path=tmp)
        s = mgr.create_session()
        mgr.update_session_from_messages(s["session_id"], [])
        updated = mgr.get_session(s["session_id"])
        assert updated["message_count"] == 0
        print("PASS: empty messages update")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_create_session,
        test_create_session_with_title,
        test_list_sessions,
        test_list_sessions_sorted_by_updated,
        test_get_session,
        test_update_session,
        test_delete_session,
        test_delete_session_removes_directory,
        test_update_session_from_messages,
        test_update_session_from_messages_long_title,
        test_update_session_preserves_existing_title,
        test_migrate_legacy_session,
        test_migrate_legacy_no_directory,
        test_sessions_file_corruption,
        test_empty_messages_update,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL: {t.__name__} - {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("ALL TESTS PASSED!")
