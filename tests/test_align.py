from phrasync.align import MIN_WORD_DURATION, align_cues


def test_alignment_never_emits_words_ending_before_their_start():
    cues = [
        {
            "id": "one",
            "start": 0.0,
            "end": 1.0,
            "text": "one",
            "words": [{"text": "one", "start": 0.9, "end": 1.0}],
        },
        {
            "id": "two",
            "start": 0.4,
            "end": 0.7,
            "text": "two three",
            "words": [
                {"text": "two", "start": 0.4, "end": 0.41},
                {"text": "three", "start": 0.42, "end": 0.43},
            ],
        },
    ]
    result = align_cues(cues, {"onsets": [], "duration": 2.0}, auto_offset=False)["cues"]
    assert result[1]["start"] >= result[0]["end"]
    for cue in result:
        previous = cue["start"]
        for word in cue["words"]:
            assert word["start"] >= previous
            assert word["end"] - word["start"] >= MIN_WORD_DURATION - 1e-4
            previous = word["end"]
        assert cue["end"] >= previous
