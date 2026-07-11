"""Utility functions for subtitle processing."""
import codecs
import json
import os
import re
import shutil
from datetime import timedelta

from config import ONEWORD_SRT_SUFFIX

SRT_BLOCK_RE = re.compile(
    r'(\d+)\s*\n'
    r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n'
    r'((?:.*\n?)*?)(?=\n\d+\s*\n|\Z)',
    re.MULTILINE,
)


def _srt_time_to_seconds(timestamp):
    hours, minutes, rest = timestamp.split(':')
    seconds, millis = rest.split(',')
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def _seconds_to_srt_time(seconds):
    millis = int(round((seconds - int(seconds)) * 1000))
    seconds = int(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def _read_text_file(file_path):
    try:
        with codecs.open(file_path, 'r', encoding='utf-8-sig') as file:
            return file.read()
    except UnicodeDecodeError:
        with codecs.open(file_path, 'r', encoding='iso-8859-1') as file:
            return file.read()


def _flatten_words_from_json(json_path):
    """Legacy fallback: extract word timings from faster-whisper segment JSON."""
    with codecs.open(json_path, 'r', encoding='utf-8-sig') as file:
        data = json.load(file)

    words = []
    for segment in data.get('segments', []):
        for word in segment.get('words') or []:
            text = word.get('word', '')
            if not text or not text.strip():
                continue
            start = word.get('start')
            end = word.get('end')
            if start is None or end is None:
                continue
            words.append({
                'start': float(start),
                'end': float(end),
                'text': text.strip(),
            })
    return words


def parse_words_from_oneword_srt(srt_path, min_duration=0.05):
    """
    Parse faster-whisper --one_word SRT into a flat word list.

    Each subtitle block is one word with its own start/end — unlike the words
    array inside JSON segments, which can stretch across silence.
    """
    content = _read_text_file(srt_path)
    lines = content.splitlines()
    words = []
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if not line.isdigit():
            index += 1
            continue

        index += 1
        if index >= len(lines):
            break
        timing_line = lines[index].strip()
        index += 1
        if index >= len(lines) or '-->' not in timing_line:
            continue

        start_text, end_text = (part.strip() for part in timing_line.split('-->', 1))
        text_line = lines[index].strip()
        index += 1
        if not text_line or '<u>' in text_line:
            continue

        start_sec = _srt_time_to_seconds(start_text)
        end_sec = _srt_time_to_seconds(end_text)
        if end_sec <= start_sec:
            end_sec = start_sec + min_duration
        words.append({
            'start': start_sec,
            'end': end_sec,
            'text': ' '.join(text_line.split()),
        })

    return words


def oneword_srt_path(srt_path):
    """Path for the preserved whisper one-word SRT beside the final karaoke SRT."""
    base, _ext = os.path.splitext(srt_path)
    return base + ONEWORD_SRT_SUFFIX


def preserve_oneword_srt(source_srt_path, dest_oneword_srt_path):
    """Keep whisper's one-word-per-line SRT before karaoke overwrites the main .srt."""
    shutil.copy2(source_srt_path, dest_oneword_srt_path)
    return True


# Default pause between words that starts a new sentence group (milliseconds).
TIKTOK_DEFAULT_SENTENCE_PAUSE_MS = 350

# Whisper one-word SRT often pads silence into a single word's duration; above this
# ratio we treat the word as a timing artifact and trim / split before it.
TIKTOK_STRETCHED_WORD_MARGIN_SEC = 0.45

SENTENCE_PUNCT_RE = re.compile(r'[.!?…]+["\']?$')
# Spoken new-thought markers; "so" is handled separately (e.g. keep "so that").
SENTENCE_STARTER_WORDS = frozenset({'okay', 'now', 'well', 'yeah', 'but'})


def _word_piece(word):
    return word['text'].strip()


def _word_duration(word):
    return float(word['end']) - float(word['start'])


def _expected_word_duration(piece):
    """Rough max spoken duration from character count (short words stay short)."""
    length = max(len(piece), 1)
    return min(0.28 + 0.11 * length, 1.8)


def _word_timing_is_stretched(word):
    piece = _word_piece(word)
    if not piece:
        return False
    return _word_duration(word) > _expected_word_duration(piece) + TIKTOK_STRETCHED_WORD_MARGIN_SEC


def _normalize_word_timings(words):
    """
    Trim whisper padding where one word's interval absorbs trailing silence.

    Padded words keep their end time but move start forward so later pause
    detection can see real gaps between phrases.
    """
    if not words:
        return []

    normalized = []
    for index, word in enumerate(words):
        piece = _word_piece(word)
        start = float(word['start'])
        end = float(word['end'])
        if piece and _word_timing_is_stretched(word):
            start = max(start, end - _expected_word_duration(piece))
        if index > 0 and start < normalized[-1]['end']:
            start = normalized[-1]['end']
        if end <= start:
            end = start + 0.05
        normalized.append({
            'start': start,
            'end': end,
            'text': word['text'],
        })
    return normalized


def _split_before_word(prev_piece, piece, next_piece=None):
    """Heuristic boundaries when whisper omits punctuation."""
    current = piece.lower()
    previous = prev_piece.lower()

    if current == 'i' and not previous.endswith("'"):
        return True

    if current in SENTENCE_STARTER_WORDS:
        if current == 'now' and previous == 'okay':
            return False
        return True

    if current == 'so' and (next_piece or '').lower() == 'that':
        return False

    return False


def _line_display_length(words):
    pieces = [_word_piece(word) for word in words if _word_piece(word)]
    if not pieces:
        return 0
    return sum(len(piece) for piece in pieces) + len(pieces) - 1


def _group_words_into_sentences(
    words,
    sentence_pause_sec=0.35,
    split_on_punctuation=True,
):
    """Group flat words into sentence bursts by pause and/or ending punctuation."""
    if not words:
        return []

    words = _normalize_word_timings(words)
    groups = [[words[0]]]
    for index, word in enumerate(words[1:], start=1):
        prev = groups[-1][-1]
        gap = float(word['start']) - float(prev['end'])
        prev_piece = _word_piece(prev)
        piece = _word_piece(word)
        next_piece = _word_piece(words[index + 1]) if index + 1 < len(words) else None
        new_sentence = gap > sentence_pause_sec
        if split_on_punctuation and SENTENCE_PUNCT_RE.search(prev_piece):
            new_sentence = True
        if _word_timing_is_stretched(word):
            new_sentence = True
        if _split_before_word(prev_piece, piece, next_piece):
            new_sentence = True
        if new_sentence:
            groups.append([word])
        else:
            groups[-1].append(word)
    return groups


def _wrap_words_by_width(words, max_line_width):
    """Greedy character wrap within one sentence."""
    lines = []
    current = []
    current_len = 0

    for word in words:
        piece = _word_piece(word)
        if not piece:
            continue
        add_len = len(piece) + (1 if current else 0)
        if current and current_len + add_len > max_line_width:
            lines.append(current)
            current = [word]
            current_len = len(piece)
        else:
            current.append(word)
            current_len += add_len

    if current:
        lines.append(current)
    return lines


def _line_index_for_word(lines, highlight_index):
    offset = 0
    for index, line in enumerate(lines):
        if highlight_index < offset + len(line):
            return index
        offset += len(line)
    return max(0, len(lines) - 1)


def _visible_lines_window(lines, highlight_index, max_line_count):
    """Pick up to max_line_count wrapped lines that include the highlighted word."""
    max_line_count = max(1, int(max_line_count))
    if not lines:
        return [], 0

    line_index = _line_index_for_word(lines, highlight_index)
    start = line_index
    if start + max_line_count > len(lines):
        start = max(0, len(lines) - max_line_count)
    return lines[start:start + max_line_count], start


def _format_sentence_highlight(lines, highlight_index, max_line_count=1):
    """Format wrapped lines with one highlighted word index (flat across lines)."""
    visible_lines, window_start = _visible_lines_window(
        lines, highlight_index, max_line_count
    )
    offset = sum(len(line) for line in lines[:window_start])
    rendered = []
    for line in visible_lines:
        parts = []
        for word in line:
            piece = _word_piece(word)
            if offset == highlight_index:
                parts.append(f'<u>{piece}</u>')
            else:
                parts.append(piece)
            offset += 1
        rendered.append(' '.join(parts))
    return '\n'.join(rendered)


def _build_sentence_group(sentence_words, group_id, max_line_width, max_line_count=1):
    """Build cues + metadata for one sentence group."""
    lines = _wrap_words_by_width(sentence_words, max_line_width)
    words_out = [
        {
            'index': index,
            'text': _word_piece(word),
            'start': float(word['start']),
            'end': float(word['end']),
        }
        for index, word in enumerate(sentence_words)
    ]

    cues_out = []
    srt_cues = []
    for index, word in enumerate(sentence_words):
        if index == 0:
            cue_start = float(word['start'])
        else:
            cue_start = float(sentence_words[index - 1]['end'])
        cue_end = float(word['end'])
        if cue_end <= cue_start:
            cue_end = cue_start + 0.05

        text = _format_sentence_highlight(lines, index, max_line_count)
        cue_entry = {
            'index': index,
            'start': cue_start,
            'end': cue_end,
            'text': text,
        }
        cues_out.append(cue_entry)
        srt_cues.append({
            'start': cue_start,
            'end': cue_end,
            'text': text,
        })

    return {
        'id': group_id,
        'start': float(sentence_words[0]['start']),
        'end': float(sentence_words[-1]['end']),
        'text': ' '.join(_word_piece(word) for word in sentence_words),
        'lines': [
            [_word_piece(word) for word in line]
            for line in lines
        ],
        'words': words_out,
        'cues': cues_out,
    }, srt_cues


def write_captions_json(groups, json_path):
    """Write TikTok sentence-group caption format."""
    payload = {
        'version': 1,
        'format': 'liver-tiktok-captions',
        'groups': groups,
    }
    with codecs.open(json_path, 'w', encoding='utf-8') as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
        file.write('\n')


def build_karaoke_srt_from_words(
    words,
    srt_path,
    max_line_width=25,
    max_line_count=1,
    sentence_pause_ms=TIKTOK_DEFAULT_SENTENCE_PAUSE_MS,
    split_on_punctuation=True,
    captions_json_path=None,
    **_legacy_kwargs,
):
    """
    Build TikTok highlight SRT from per-word timings.

    1. Group words into sentences (pause + optional punctuation split)
    2. Wrap each sentence to max_line_width
    3. Emit continuous <u> cues within each sentence group (max_line_count lines visible)
    """
    del _legacy_kwargs

    if not words:
        return False

    sentence_pause_sec = max(float(sentence_pause_ms), 0) / 1000.0
    sentence_groups = _group_words_into_sentences(
        words,
        sentence_pause_sec=sentence_pause_sec,
        split_on_punctuation=split_on_punctuation,
    )

    groups_out = []
    srt_cues = []
    for group_id, sentence_words in enumerate(sentence_groups, start=1):
        group_data, group_cues = _build_sentence_group(
            sentence_words,
            group_id,
            max_line_width,
            max_line_count=max_line_count,
        )
        groups_out.append(group_data)
        srt_cues.extend(group_cues)

    lines_out = []
    for index, cue in enumerate(srt_cues, start=1):
        lines_out.append(str(index))
        lines_out.append(
            f"{_seconds_to_srt_time(cue['start'])} --> "
            f"{_seconds_to_srt_time(cue['end'])}"
        )
        lines_out.append(cue['text'])
        lines_out.append('')

    with codecs.open(srt_path, 'w', encoding='utf-8') as file:
        file.write('\n'.join(lines_out).rstrip() + '\n')

    if captions_json_path:
        write_captions_json(groups_out, captions_json_path)

    return True


def read_words_from_captions_json(json_path):
    """Flatten per-word timings stored in a .captions.json file."""
    with codecs.open(json_path, 'r', encoding='utf-8-sig') as file:
        data = json.load(file)

    words = []
    for group in data.get('groups', []):
        for entry in group.get('words', []):
            text = entry.get('text', '')
            if not text or not str(text).strip():
                continue
            start = entry.get('start')
            end = entry.get('end')
            if start is None or end is None:
                continue
            words.append({
                'start': float(start),
                'end': float(end),
                'text': str(text).strip(),
            })
    return words


def prepare_karaoke_srt_from_oneword(
    oneword_srt_path,
    output_srt_path,
    max_line_width=25,
    max_line_count=1,
    sentence_pause_ms=TIKTOK_DEFAULT_SENTENCE_PAUSE_MS,
    split_on_punctuation=True,
    captions_json_path=None,
    **_legacy_kwargs,
):
    """Parse whisper one-word SRT in memory and build karaoke SRT."""
    del _legacy_kwargs
    words = parse_words_from_oneword_srt(oneword_srt_path)
    if not words:
        return False
    return build_karaoke_srt_from_words(
        words,
        output_srt_path,
        max_line_width=max_line_width,
        max_line_count=max_line_count,
        sentence_pause_ms=sentence_pause_ms,
        split_on_punctuation=split_on_punctuation,
        captions_json_path=captions_json_path,
    )


def rebuild_karaoke_from_captions_json(
    captions_json_path,
    output_srt_path,
    max_line_width=25,
    max_line_count=1,
    sentence_pause_ms=TIKTOK_DEFAULT_SENTENCE_PAUSE_MS,
    split_on_punctuation=True,
    **_legacy_kwargs,
):
    """Rebuild karaoke SRT from a previously saved .captions.json file."""
    del _legacy_kwargs
    words = read_words_from_captions_json(captions_json_path)
    return build_karaoke_srt_from_words(
        words,
        output_srt_path,
        max_line_width=max_line_width,
        max_line_count=max_line_count,
        sentence_pause_ms=sentence_pause_ms,
        split_on_punctuation=split_on_punctuation,
        captions_json_path=captions_json_path,
    )


def build_karaoke_srt_from_json(
    json_path,
    srt_path,
    max_line_width=25,
    max_line_count=1,
    sentence_pause_ms=TIKTOK_DEFAULT_SENTENCE_PAUSE_MS,
    split_on_punctuation=True,
    captions_json_path=None,
    **_legacy_kwargs,
):
    """Legacy fallback when only faster-whisper segment JSON is available."""
    del _legacy_kwargs
    words = _flatten_words_from_json(json_path)
    return build_karaoke_srt_from_words(
        words,
        srt_path,
        max_line_width=max_line_width,
        max_line_count=max_line_count,
        sentence_pause_ms=sentence_pause_ms,
        split_on_punctuation=split_on_punctuation,
        captions_json_path=captions_json_path,
    )


def fix_highlight_srt_gaps(file_path, max_cue_duration=0.85, long_cue_threshold=1.0):
    """
    Trim highlight-style cues that stretch across silence.

    faster-whisper highlight_words can emit rolling <u> cues that stay on screen
    for several seconds during quiet parts. Cap those to a short window so the
    timeline has real pauses with no subtitles.
    """
    try:
        content = _read_text_file(file_path)
    except OSError:
        return False

    if '<u>' not in content:
        return False

    blocks = []
    for match in SRT_BLOCK_RE.finditer(content):
        index, start, end, text = match.groups()
        start_sec = _srt_time_to_seconds(start)
        end_sec = _srt_time_to_seconds(end)
        duration = end_sec - start_sec
        if duration > long_cue_threshold:
            end_sec = start_sec + max_cue_duration
        blocks.append({
            'start': start_sec,
            'end': end_sec,
            'text': text.rstrip('\n'),
        })

    if not blocks:
        return False

    # Drop cues fully swallowed by a later speech burst after a long pause.
    cleaned = []
    for i, block in enumerate(blocks):
        if i > 0:
            prev = blocks[i - 1]
            gap = block['start'] - prev['end']
            if gap > 1.5 and block['end'] - block['start'] > long_cue_threshold:
                block['end'] = block['start'] + max_cue_duration
        if cleaned:
            pause = block['start'] - cleaned[-1]['end']
            if pause > 2.0 and block['start'] - cleaned[-1]['start'] > 2.0:
                while cleaned and cleaned[-1]['end'] > block['start'] - 0.05:
                    cleaned.pop()
        cleaned.append(block)

    lines = []
    for index, block in enumerate(cleaned, start=1):
        lines.append(str(index))
        lines.append(
            f"{_seconds_to_srt_time(block['start'])} --> "
            f"{_seconds_to_srt_time(block['end'])}"
        )
        lines.append(block['text'])
        lines.append('')

    with codecs.open(file_path, 'w', encoding='utf-8') as file:
        file.write('\n'.join(lines).rstrip() + '\n')

    return True


def clean_srt(file_path):
    """Clean and normalize SRT subtitle file."""
    try:
        content = _read_text_file(file_path)
    except OSError:
        return

    # Remove BOM if present
    content = content.lstrip('\ufeff')

    # Remove non-printable characters except newlines and CJK characters
    content = re.sub(
        r'[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u1100-\u11ff'
        r'\u3130-\u318f\ua960-\ua97f\uac00-\ud7af\u4e00-\u9fff\x20-\x7E\n]',
        '', content
    )

    # Fix common encoding issues
    content = content.replace('â€™', "'")
    content = content.replace('â€"', "–")
    content = content.replace('â€œ', '"')
    content = content.replace('â€', '"')

    with codecs.open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

    print(f"Cleaned SRT file has been saved as {file_path}")


def format_timestamp(seconds):
    """Format seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    delta = timedelta(seconds=seconds)
    hours, remainder = divmod(delta.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"


def format_timestamp_from_match(minutes, sec_mili):
    """Format timestamp from regex match groups."""
    total_seconds = float(minutes) * 60 + float(sec_mili)
    secint = int(total_seconds)
    milliseconds = int((total_seconds - secint) * 1000)
    hours, minutes = divmod(secint, 3600)
    minutes, seconds = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

