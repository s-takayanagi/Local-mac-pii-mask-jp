import sys
sys.path.insert(0, ".")

from unittest.mock import patch, MagicMock
import requests

from ui.streamlit_app import check_lm_studio_connection, _build_replacement_log_text


# ===========================================================
# check_lm_studio_connection のテスト
# ===========================================================

class TestCheckLmStudioConnection:
    def test_success_returns_ok_true(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "qwen/qwen3.5-9b"}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            result = check_lm_studio_connection("http://localhost:1234/v1/chat/completions")

        assert result["ok"] is True
        assert result["error"] is None
        assert "qwen/qwen3.5-9b" in result["models"]

    def test_connection_error_returns_ok_false(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError()):
            result = check_lm_studio_connection("http://localhost:1234/v1/chat/completions")

        assert result["ok"] is False
        assert result["error"] is not None
        assert len(result["models"]) > 0  # デフォルトモデルが入る

    def test_timeout_returns_ok_false(self):
        with patch("requests.get", side_effect=requests.exceptions.Timeout()):
            result = check_lm_studio_connection("http://localhost:1234/v1/chat/completions")

        assert result["ok"] is False
        assert "タイムアウト" in result["error"]

    def test_empty_model_list_returns_default(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            result = check_lm_studio_connection("http://localhost:1234/v1/chat/completions")

        assert result["ok"] is True
        assert len(result["models"]) > 0  # デフォルトモデルがフォールバック

    def test_http_error_returns_ok_false(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError()
        with patch("requests.get", return_value=mock_resp):
            result = check_lm_studio_connection("http://localhost:1234/v1/chat/completions")

        assert result["ok"] is False

    def test_url_parsing_uses_base_url(self):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": []}
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            check_lm_studio_connection("http://localhost:1234/v1/chat/completions")

        called_url = mock_get.call_args[0][0]
        assert called_url == "http://localhost:1234/v1/models"
        assert "chat" not in called_url


# ===========================================================
# _build_replacement_log_text のテスト
# ===========================================================

class TestBuildReplacementLogText:
    def test_empty_entries_returns_placeholder(self):
        text = _build_replacement_log_text([])
        assert "置換なし" in text

    def test_single_entry_formatted(self):
        entries = [{
            "file": "test.xlsx",
            "location": "Sheet1!A1",
            "layer": "layer1",
            "original": "山田太郎",
            "tag": "[氏名]",
        }]
        text = _build_replacement_log_text(entries)
        assert "test.xlsx" in text
        assert "山田太郎" in text
        assert "[氏名]" in text
        assert "Sheet1!A1" in text

    def test_multiple_files_grouped(self):
        entries = [
            {"file": "a.xlsx", "location": "A1", "layer": "layer1", "original": "山田", "tag": "[氏名]"},
            {"file": "b.xlsx", "location": "A1", "layer": "layer1", "original": "田中", "tag": "[氏名]"},
        ]
        text = _build_replacement_log_text(entries)
        assert "[a.xlsx]" in text
        assert "[b.xlsx]" in text

    def test_total_count_shown(self):
        entries = [
            {"file": "a.xlsx", "location": "A1", "layer": "layer1", "original": "山田", "tag": "[氏名]"},
            {"file": "a.xlsx", "location": "B1", "layer": "layer1", "original": "田中", "tag": "[氏名]"},
        ]
        text = _build_replacement_log_text(entries)
        assert "2 件" in text

    def test_layer_label_displayed(self):
        entries = [{
            "file": "test.xlsx",
            "location": "A1",
            "layer": "layer1",
            "original": "090-1234-5678",
            "tag": "[電話番号]",
        }]
        text = _build_replacement_log_text(entries)
        assert "Layer 1" in text

    def test_header_present(self):
        entries = [{
            "file": "f.xlsx", "location": "A1", "layer": "layer2",
            "original": "山田太郎", "tag": "[氏名]",
        }]
        text = _build_replacement_log_text(entries)
        assert "PII マスキングログ" in text


# ===========================================================
# Streamlit AppTest (基本レンダリング)
# ===========================================================

def test_streamlit_app_renders_without_exception():
    """LM Studio 接続状態に関わらずアプリが正常にレンダリングされる"""
    pytest = __import__("pytest")
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        pytest.skip("streamlit.testing.v1 が利用できません")

    at = AppTest.from_file("ui/streamlit_app.py", default_timeout=30)
    at.run()

    assert not at.exception
    # LM Studio の状態（接続中 or 未接続）がサイドバーに表示される
    all_texts = (
        [e.value for e in at.sidebar.success]
        + [e.value for e in at.sidebar.error]
        + [e.value for e in at.success]
        + [e.value for e in at.error]
    )
    assert any("LM Studio" in t for t in all_texts)


def test_streamlit_app_button_disabled_without_folder():
    """フォルダ未入力時はマスキング開始ボタンが disabled"""
    pytest = __import__("pytest")
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        pytest.skip("streamlit.testing.v1 が利用できません")

    with patch("ui.streamlit_app.check_lm_studio_connection", return_value={
        "ok": True,
        "models": ["qwen/qwen3.5-9b"],
        "error": None,
    }):
        at = AppTest.from_file("ui/streamlit_app.py", default_timeout=30)
        at.run()

    assert not at.exception
    buttons = at.button
    start_buttons = [b for b in buttons if "マスキング開始" in b.label]
    assert len(start_buttons) > 0
    assert start_buttons[0].disabled


def test_streamlit_run_masking_invalid_folder(tmp_path):
    """存在しないフォルダを指定すると st.error が呼ばれる"""
    pytest = __import__("pytest")
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        pytest.skip("streamlit.testing.v1 が利用できません")

    with patch("ui.streamlit_app.check_lm_studio_connection", return_value={
        "ok": True,
        "models": ["qwen/qwen3.5-9b"],
        "error": None,
    }):
        at = AppTest.from_file("ui/streamlit_app.py", default_timeout=30)
        at.run()
        at.text_input[0].set_value("/nonexistent/path/xyz")
        at.run()
        at.button[0].click()
        at.run()

    assert not at.exception
