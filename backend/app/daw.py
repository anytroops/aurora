"""Parsers for DAW project files: Ableton Live (.als) and REAPER (.rpp).

Both parsers return the same shape:
{daw, filename, tempo_bpm, track_count, clip_count, plugin_count, tracks:
 [{name, type, devices, clip_count}]}
"""

import gzip
import re
import xml.etree.ElementTree as ET

ABLETON_TRACK_TAGS = {
    "AudioTrack": "audio",
    "MidiTrack": "midi",
    "ReturnTrack": "return",
    "GroupTrack": "group",
}

# Prettier names for common built-in Ableton devices (raw tag is the fallback)
ABLETON_DEVICE_NAMES = {
    "Eq8": "EQ Eight",
    "Compressor2": "Compressor",
    "GlueCompressor": "Glue Compressor",
    "AutoFilter": "Auto Filter",
    "Reverb": "Reverb",
    "Delay": "Delay",
    "Saturator": "Saturator",
    "Operator": "Operator",
    "Wavetable": "Wavetable",
    "OriginalSimpler": "Simpler",
    "MultiSampler": "Sampler",
    "DrumGroupDevice": "Drum Rack",
    "InstrumentGroupDevice": "Instrument Rack",
    "AudioEffectGroupDevice": "Audio Effect Rack",
    "Limiter": "Limiter",
    "Gate": "Gate",
    "ChannelEq": "Channel EQ",
}


def parse_project(data: bytes, filename: str) -> dict:
    lowered = filename.lower()
    if lowered.endswith(".als"):
        return _parse_ableton(data, filename)
    if lowered.endswith(".rpp"):
        return _parse_reaper(data, filename)
    raise ValueError("Unsupported project format — upload an .als (Ableton) or .rpp (REAPER) file.")


def _summarize(daw: str, filename: str, tempo: float | None, tracks: list[dict]) -> dict:
    return {
        "daw": daw,
        "filename": filename,
        "tempo_bpm": tempo,
        "track_count": len(tracks),
        "clip_count": sum(t["clip_count"] for t in tracks),
        "plugin_count": sum(len(t["devices"]) for t in tracks),
        "tracks": tracks,
    }


# ---------------------------------------------------------------- Ableton

def _ableton_device_name(dev: ET.Element) -> str:
    if dev.tag in ("PluginDevice", "AuPluginDevice"):
        for path in (
            "PluginDesc/VstPluginInfo/PlugName",
            "PluginDesc/Vst3PluginInfo/Name",
            "PluginDesc/AuPluginInfo/Name",
        ):
            el = dev.find(path)
            if el is not None and el.get("Value"):
                return el.get("Value")
        return "Unknown plugin"
    return ABLETON_DEVICE_NAMES.get(dev.tag, dev.tag)


def _parse_ableton(data: bytes, filename: str) -> dict:
    try:
        xml_bytes = gzip.decompress(data)
    except (OSError, gzip.BadGzipFile):
        xml_bytes = data  # some exporters write the XML uncompressed
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        raise ValueError("Not a readable Ableton Live set (bad XML).")
    live_set = root.find("LiveSet")
    if root.tag != "Ableton" or live_set is None:
        raise ValueError("Not an Ableton Live set.")

    tempo = None
    manual = live_set.find(".//Tempo/Manual")
    if manual is not None:
        try:
            tempo = float(manual.get("Value", ""))
        except ValueError:
            pass

    tracks = []
    tracks_el = live_set.find("Tracks")
    for el in tracks_el if tracks_el is not None else []:
        track_type = ABLETON_TRACK_TAGS.get(el.tag)
        if track_type is None:
            continue
        name_el = el.find("Name/EffectiveName")
        name = (name_el.get("Value") if name_el is not None else None) or el.tag

        devices_el = el.find("DeviceChain/DeviceChain/Devices")
        if devices_el is None:
            devices_el = el.find("DeviceChain/Devices")
        devices = [
            _ableton_device_name(d) for d in (devices_el if devices_el is not None else [])
        ]

        clip_count = len(el.findall(".//AudioClip")) + len(el.findall(".//MidiClip"))
        tracks.append(
            {"name": name, "type": track_type, "devices": devices, "clip_count": clip_count}
        )

    return _summarize("Ableton Live", filename, tempo, tracks)


# ---------------------------------------------------------------- REAPER

_RPP_FX = re.compile(r'<(?:VST3?|CLAP|AU|DX|JS|LV2)\b\s+(?:"([^"]*)"|(\S+))')
_RPP_NAME = re.compile(r'NAME\s+(?:"(.*)"|(\S+))')


def _parse_reaper(data: bytes, filename: str) -> dict:
    text = data.decode("utf-8", errors="replace")
    if not text.lstrip().startswith("<REAPER_PROJECT"):
        raise ValueError("Not a REAPER project file.")

    tempo = None
    tracks: list[dict] = []
    current: dict | None = None
    stack: list[str] = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("<"):
            tag = line[1:].split(None, 1)[0] if len(line) > 1 else ""
            if tag == "TRACK":
                current = {"name": "", "type": "track", "devices": [], "clip_count": 0}
                tracks.append(current)
            elif tag == "ITEM" and current is not None:
                current["clip_count"] += 1
            elif current is not None and "FXCHAIN" in stack:
                m = _RPP_FX.match(line)
                if m:
                    current["devices"].append(m.group(1) or m.group(2))
            stack.append(tag)
        elif line.startswith(">"):
            if stack:
                closed = stack.pop()
                if closed == "TRACK":
                    current = None
        elif line.startswith("TEMPO ") and stack and stack[-1] == "REAPER_PROJECT":
            try:
                tempo = float(line.split()[1])
            except (IndexError, ValueError):
                pass
        elif (
            line.startswith("NAME")
            and current is not None
            and stack
            and stack[-1] == "TRACK"
            and not current["name"]
        ):
            m = _RPP_NAME.match(line)
            if m:
                current["name"] = m.group(1) if m.group(1) is not None else m.group(2)

    for i, t in enumerate(tracks):
        if not t["name"]:
            t["name"] = f"Track {i + 1}"

    return _summarize("REAPER", filename, tempo, tracks)
