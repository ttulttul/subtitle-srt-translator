"""Tests for SRT parsing and rendering."""

from subtitle_srt_translator.models import SubtitleCue
from subtitle_srt_translator.srt import parse_srt, render_srt, replace_cue_text


def test_parse_idless_srt_preserves_timing_metadata() -> None:
    """ID-less SRT blocks with speaker metadata are parsed as cues."""
    cues = parse_srt(
        "00:00:00,080 --> 00:00:04,520 [Speaker 0]\n"
        "[רעשי רוח]\n\n"
        "00:00:07,160 --> 00:00:09,320 [Speaker 0]\n"
        "Hello\n"
    )

    assert cues == (
        SubtitleCue(
            index=1,
            cue_id=None,
            timing="00:00:00,080 --> 00:00:04,520 [Speaker 0]",
            text_lines=("[רעשי רוח]",),
        ),
        SubtitleCue(
            index=2,
            cue_id=None,
            timing="00:00:07,160 --> 00:00:09,320 [Speaker 0]",
            text_lines=("Hello",),
        ),
    )


def test_render_standard_srt_preserves_cue_id() -> None:
    """Standard numbered SRT cues render with cue IDs."""
    cues = parse_srt("12\n00:00:01,000 --> 00:00:02,000\nHi\nthere\n")

    output = render_srt(cues)

    assert output == "12\n00:00:01,000 --> 00:00:02,000\nHi\nthere\n"


def test_replace_cue_text_substitutes_translation() -> None:
    """Cue text replacement keeps cue metadata intact."""
    cues = (
        SubtitleCue(
            index=1,
            cue_id="1",
            timing="00:00:01,000 --> 00:00:02,000",
            text_lines=("שלום",),
        ),
    )

    replaced = replace_cue_text(cues, {1: ("Hello",)})

    assert replaced[0].cue_id == "1"
    assert replaced[0].timing == "00:00:01,000 --> 00:00:02,000"
    assert replaced[0].text_lines == ("Hello",)
