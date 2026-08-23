from pathlib import Path

import os

from phrasync.settings import hf_token_status, remove_hf_token, save_hf_token, saved_hf_token


def test_hugging_face_token_lifecycle(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.delenv("HF_TOKEN", raising=False)
    status = save_hf_token("hf_test_token_123456789", path)
    assert status["configured"] is True
    assert status["source"] == "saved"
    assert status["masked"].endswith("6789")
    assert saved_hf_token(path) == "hf_test_token_123456789"
    assert os.environ["HF_TOKEN"] == "hf_test_token_123456789"
    status = remove_hf_token(path)
    assert status["configured"] is False
    assert not path.exists()
    assert "HF_TOKEN" not in os.environ


def test_environment_token_is_never_returned(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_TOKEN", "hf_environment_secret_9876")
    status = hf_token_status(tmp_path / "missing.json")
    assert status == {
        "configured": True,
        "masked": "hf_••••••••9876",
        "source": "environment",
        "canRemove": False,
    }


def test_assets_resolve_after_the_workspace_moves(tmp_path, monkeypatch):
    """An asset must be found by id even when its sidecar records an old path.

    The workspace folder can move — a rename, a different user profile, a
    restored backup — and every sidecar then holds a dead absolute path. Before
    this was fixed, transcription and rendering failed while the file sat right
    there next to its metadata.
    """
    import json

    from phrasync import storage

    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True)
    monkeypatch.setattr(storage, "UPLOADS_DIR", uploads)

    asset_id = "abc123.wav"
    (uploads / asset_id).write_bytes(b"RIFF....")
    (uploads / f"{asset_id}.meta.json").write_text(
        json.dumps({
            "id": asset_id,
            "kind": "audio",
            "name": "song.wav",
            "path": r"C:\somewhere\that\no\longer\exists\abc123.wav",
            "size": 8,
            "extension": ".wav",
        }),
        encoding="utf-8",
    )

    asset = storage.get_asset(asset_id, "audio")
    assert asset is not None
    assert Path(asset.path) == uploads / asset_id
    assert Path(asset.path).exists()

    listed = storage.list_assets()
    assert [item["id"] for item in listed] == [asset_id]
