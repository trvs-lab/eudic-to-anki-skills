INFLICT_WORD_FAMILY = (
    "拆解：in-「在……上」+ flict「打击」→ inflict「v. 使遭受；造成」\n"
    "联想：conflict「n. 冲突」、afflict「v. 使痛苦」"
)

# Three complete MPEG-1 Layer III frames, 128 kbps / 44.1 kHz, with silent data.
VALID_MP3_BYTES = (b"\xff\xfb\x90\x00" + bytes(413)) * 3
