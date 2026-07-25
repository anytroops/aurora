import gzip

import pytest

from app.daw import parse_project


def test_reaper_structure(reaper_bytes):
    p = parse_project(reaper_bytes, "test.rpp")
    assert p["daw"] == "REAPER"
    assert p["tempo_bpm"] == 128.0
    assert p["track_count"] == 3
    assert p["clip_count"] == 4
    assert p["plugin_count"] == 3
    assert [t["name"] for t in p["tracks"]] == ["Drums", "Bass", "Vox Lead"]


def test_reaper_devices_and_clips(reaper_bytes):
    tracks = {t["name"]: t for t in parse_project(reaper_bytes, "t.rpp")["tracks"]}
    assert tracks["Drums"]["clip_count"] == 2
    assert tracks["Drums"]["devices"] == [
        "VST3: Pro-Q 3 (FabFilter)",
        "VST: ReaComp (Cockos)",
    ]
    # A track with no FXCHAIN must report an empty chain, not inherit the previous one
    assert tracks["Vox Lead"]["devices"] == []


def test_reaper_unnamed_track_gets_placeholder():
    rpp = b'<REAPER_PROJECT 0.1 "7" 1\n  <TRACK {1}\n  >\n>\n'
    p = parse_project(rpp, "x.rpp")
    assert p["tracks"][0]["name"] == "Track 1"


def test_ableton_structure(ableton_bytes):
    p = parse_project(ableton_bytes, "test.als")
    assert p["daw"] == "Ableton Live"
    assert p["tempo_bpm"] == 124.0
    assert p["track_count"] == 3
    assert p["plugin_count"] == 7


def test_ableton_track_types_and_device_names(ableton_bytes):
    tracks = {t["name"]: t for t in parse_project(ableton_bytes, "t.als")["tracks"]}
    assert tracks["Bass"]["type"] == "midi"
    assert tracks["Vocals"]["type"] == "audio"
    assert tracks["A-Reverb"]["type"] == "return"
    # Built-in tags map to display names; plugin devices use their real name
    assert tracks["Vocals"]["devices"] == ["EQ Eight", "Compressor", "FabFilter Pro-Q 3"]
    assert "Serum" in tracks["Bass"]["devices"]


def test_ableton_counts_midi_and_audio_clips(ableton_bytes):
    tracks = {t["name"]: t for t in parse_project(ableton_bytes, "t.als")["tracks"]}
    assert tracks["Bass"]["clip_count"] == 2
    assert tracks["Vocals"]["clip_count"] == 1


def test_ableton_accepts_uncompressed_xml():
    from tests.conftest import ABLETON_PROJECT

    p = parse_project(ABLETON_PROJECT.encode(), "plain.als")
    assert p["track_count"] == 3


def test_unsupported_extension_rejected():
    with pytest.raises(ValueError, match="Unsupported project format"):
        parse_project(b"whatever", "song.flp")


def test_bad_ableton_xml_rejected():
    with pytest.raises(ValueError, match="bad XML"):
        parse_project(gzip.compress(b"<Ableton><oops"), "broken.als")


def test_non_ableton_xml_rejected():
    with pytest.raises(ValueError, match="Not an Ableton"):
        parse_project(gzip.compress(b"<Something><Else/></Something>"), "x.als")


def test_non_reaper_text_rejected():
    with pytest.raises(ValueError, match="Not a REAPER"):
        parse_project(b"just some text", "x.rpp")
