"""Utility functions for subtitle processing."""
import codecs
import json
import re
from datetime import timedelta

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


def write_words_json(words, json_path):
    """Save one normalized entry per word for karaoke rebuild."""
    payload = {
        'words': [
            {
                'start': word['start'],
                'end': word['end'],
                'text': word['text'],
            }
            for word in words
        ],
    }
    with codecs.open(json_path, 'w', encoding='utf-8') as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
        file.write('\n')


def read_words_json(json_path):
    with codecs.open(json_path, 'r', encoding='utf-8-sig') as file:
        data = json.load(file)

    words = []
    for entry in data.get('words', []):
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


def _group_words_into_segments(words, silence_gap=0.35):
    """Split a flat word list into speech bursts separated by silence."""
    if not words:
        return []

    segments = [[words[0]]]
    for word in words[1:]:
        gap = word['start'] - segments[-1][-1]['end']
        if gap > silence_gap:
            segments.append([word])
        else:
            segments[-1].append(word)
    return segments


STRONG_BREAK_RE = re.compile(r'[.!?…]+["\']?$')
COMMA_BREAK_RE = re.compile(r',["\']?$')
COLON_BREAK_RE = re.compile(r':["\']?$')
DANGLING_STARTERS = frozenset({
    'a', 'an', 'the', 'i', 'to', 'of', 'in', 'on', 'at', 'it', 'is', 'my', 'we',
    'he', 'she', 'or', 'and', 'but', 'so', 'if', 'as', 'be', 'do', 'no', 'not',
})
DANGLING_ENDINGS = frozenset({
    'a', 'an', 'the', 'i', 'to', 'of', 'in', 'on', 'at', 'it', 'is', 'my', 'we',
    'he', 'she', 'or', 'and', 'but', 'so', 'if', 'as', 'be', 'do', 'with', 'for',
})
# Idiomatic / grammatical chains — avoid splitting these across lines when possible.
PHRASE_CHAINS = (
    ('why', 'the', 'fuck'),
    ('why', 'the', 'hell'),
    ('i', "don't", 'know'),
    ('turn', 'off'),
    ('low', 'power', 'mode'),
    ('power', 'mode'),
    ('ha', 'ha'),
)


def _split_inside_phrase(line_cores, next_core):
    """Penalty when a break would split a known phrase chain mid-line."""
    if not line_cores or next_core is None:
        return 0
    for chain in PHRASE_CHAINS:
        for index in range(len(chain) - 1):
            if line_cores[-1] == chain[index] and next_core == chain[index + 1]:
                # Breaking before a phrase starts on the next line is fine (e.g. …|why the fuck).
                if index == 0:
                    return 0
                return -90
    return 0


def _word_piece(word):
    return word['text'].strip()


def _word_core(word):
    return re.sub(r'^[^\w]+|[^\w]+$', '', _word_piece(word).lower())


def _line_display_length(words):
    pieces = [_word_piece(word) for word in words if _word_piece(word)]
    if not pieces:
        return 0
    return sum(len(piece) for piece in pieces) + len(pieces) - 1


def _break_score(line_words, max_line_width, next_word=None, comma_break_percent=70):
    """Score how good a line break is after line_words (higher = better)."""
    if not line_words:
        return -10_000

    line_len = _line_display_length(line_words)
    last_piece = _word_piece(line_words[-1])
    score = line_len

    if STRONG_BREAK_RE.search(last_piece):
        score += 120
    elif COMMA_BREAK_RE.search(last_piece):
        threshold = max_line_width * (comma_break_percent / 100.0)
        if line_len >= threshold:
            score += 80
        else:
            score += 25
    elif COLON_BREAK_RE.search(last_piece):
        score += 50

    fill_ratio = line_len / max(max_line_width, 1)
    if fill_ratio >= 0.85:
        score += 30
    elif fill_ratio >= 0.65:
        score += 15
    elif fill_ratio < 0.35 and not STRONG_BREAK_RE.search(last_piece):
        score -= 35

    if _word_core(line_words[-1]) in DANGLING_ENDINGS and not STRONG_BREAK_RE.search(last_piece):
        score -= 45

    if next_word is not None:
        next_core = _word_core(next_word)
        line_cores = [_word_core(word) for word in line_words]
        score += _split_inside_phrase(line_cores, next_core)
        if next_core in DANGLING_STARTERS and fill_ratio < 0.75:
            score -= 20
        if len(line_words) == 1 and next_core in DANGLING_STARTERS:
            score -= 25

    return score


def _incomplete_phrase_at_end(cores):
    """True when the line ends mid-phrase and should pull more words."""
    if not cores:
        return False
    for chain in PHRASE_CHAINS:
        for taken in range(1, len(chain)):
            if cores[-taken:] == list(chain[:taken]):
                return True
    return False


def _wrap_segment_words(words, max_line_width, comma_break_percent=70):
    """
    Break one speech segment into display lines.

    Prefers breaks at punctuation and balanced line lengths instead of a hard
    character cutoff mid-phrase.
    """
    if not words:
        return []

    lines = []
    index = 0
    total = len(words)

    while index < total:
        best_end = index + 1
        best_score = -10_000

        for end in range(index + 1, total + 1):
            line_words = words[index:end]
            line_len = _line_display_length(line_words)
            if line_len > max_line_width:
                break

            next_word = words[end] if end < total else None
            score = _break_score(
                line_words,
                max_line_width,
                next_word=next_word,
                comma_break_percent=comma_break_percent,
            )
            if score > best_score:
                best_score = score
                best_end = end

        if best_end <= index:
            best_end = index + 1

        # Finish partial phrases (e.g. "why the") when they still fit on the line.
        while best_end < total:
            line_words = words[index:best_end]
            cores = [_word_core(word) for word in line_words]
            if not _incomplete_phrase_at_end(cores):
                break
            extended = words[index:best_end + 1]
            if _line_display_length(extended) > max_line_width:
                break
            best_end += 1

        line_words = words[index:best_end]
        cores = [_word_core(word) for word in line_words]
        if _incomplete_phrase_at_end(cores):
            for chain in PHRASE_CHAINS:
                for taken in range(1, len(chain)):
                    if cores[-taken:] == list(chain[:taken]):
                        best_end -= taken - 1
                        break
                else:
                    continue
                break
            if best_end <= index:
                best_end = index + 1

        lines.append(words[index:best_end])
        index = best_end

    return _balance_wrapped_lines(lines, max_line_width)


def _balance_wrapped_lines(lines, max_line_width):
    """Pull orphan words across line boundaries when it reads more naturally."""
    if len(lines) < 2:
        return lines

    balanced = [list(line) for line in lines]

    for line_index in range(len(balanced) - 1):
        current = balanced[line_index]
        nxt = balanced[line_index + 1]
        if not current or not nxt:
            continue

        # Move a trailing dangling word down when the next line is a single orphan.
        if len(nxt) == 1 and _word_core(current[-1]) in DANGLING_ENDINGS:
            moved = current.pop()
            trial = [moved] + nxt
            if _line_display_length(trial) <= max_line_width:
                balanced[line_index + 1] = trial
                continue

        # Pull a leading starter word up when the next line would begin with one alone.
        if len(nxt) == 1 and _word_core(nxt[0]) in DANGLING_STARTERS:
            trial = current + nxt
            if _line_display_length(trial) <= max_line_width:
                balanced[line_index] = trial
                balanced[line_index + 1] = []

        # Avoid one-word lines sandwiched between longer ones when merge fits.
        if len(current) == 1 and line_index > 0:
            prev = balanced[line_index - 1]
            if prev and _line_display_length(prev + current) <= max_line_width:
                balanced[line_index - 1] = prev + current
                balanced[line_index] = []

    return [line for line in balanced if line]


def _group_lines(lines, max_line_count):
    max_line_count = max(1, int(max_line_count))
    groups = []
    for index in range(0, len(lines), max_line_count):
        groups.append(lines[index:index + max_line_count])
    return groups


def _format_karaoke_block(line_groups, highlight_word_index):
    """Format one or more lines with a single highlighted word."""
    flat_words = [word for line in line_groups for word in line]
    lines = []
    offset = 0
    for line in line_groups:
        parts = []
        for local_index, word in enumerate(line):
            global_index = offset + local_index
            piece = word['text'].strip()
            if global_index == highlight_word_index:
                parts.append(f'<u>{piece}</u>')
            else:
                parts.append(piece)
        lines.append(' '.join(parts))
        offset += len(line)
    return '\n'.join(lines), flat_words


def _cue_end_for_word(word, min_duration=0.05):
    """Use the word's own end time — no stretching into the next word or silence."""
    end_sec = float(word['end'])
    start_sec = float(word['start'])
    if end_sec <= start_sec:
        end_sec = start_sec + min_duration
    return end_sec


def build_karaoke_srt_from_words(
    words,
    srt_path,
    max_line_width=25,
    max_line_count=1,
    silence_gap=0.35,
    comma_break_percent=70,
):
    """Build rolling <u> highlight SRT from a flat per-word timing list."""
    if not words:
        return False

    segments = _group_words_into_segments(words, silence_gap)

    blocks = []
    for segment_words in segments:
        lines = _wrap_segment_words(
            segment_words,
            max_line_width,
            comma_break_percent=comma_break_percent,
        )
        blocks.extend(_group_lines(lines, max_line_count))

    cues = []
    for block in blocks:
        block_words = [word for line in block for word in line]
        for index in range(len(block_words)):
            start = block_words[index]['start']
            end = _cue_end_for_word(block_words[index])
            if end <= start:
                end = start + 0.05
            text, _ = _format_karaoke_block(block, index)
            cues.append({'start': start, 'end': end, 'text': text})

    lines_out = []
    for index, cue in enumerate(cues, start=1):
        lines_out.append(str(index))
        lines_out.append(
            f"{_seconds_to_srt_time(cue['start'])} --> "
            f"{_seconds_to_srt_time(cue['end'])}"
        )
        lines_out.append(cue['text'])
        lines_out.append('')

    with codecs.open(srt_path, 'w', encoding='utf-8') as file:
        file.write('\n'.join(lines_out).rstrip() + '\n')

    return True


def prepare_karaoke_srt_from_oneword(
    oneword_srt_path,
    words_json_path,
    output_srt_path,
    max_line_width=25,
    max_line_count=1,
    silence_gap=0.35,
    comma_break_percent=70,
):
    """Parse one-word-per-line SRT, save .words.json, and build karaoke SRT."""
    words = parse_words_from_oneword_srt(oneword_srt_path)
    if not words:
        return False
    write_words_json(words, words_json_path)
    return build_karaoke_srt_from_words(
        words,
        output_srt_path,
        max_line_width=max_line_width,
        max_line_count=max_line_count,
        silence_gap=silence_gap,
        comma_break_percent=comma_break_percent,
    )


def rebuild_karaoke_from_words_json(
    words_json_path,
    output_srt_path,
    max_line_width=25,
    max_line_count=1,
    silence_gap=0.35,
    comma_break_percent=70,
):
    """Rebuild karaoke SRT from a previously saved .words.json file."""
    words = read_words_json(words_json_path)
    return build_karaoke_srt_from_words(
        words,
        output_srt_path,
        max_line_width=max_line_width,
        max_line_count=max_line_count,
        silence_gap=silence_gap,
        comma_break_percent=comma_break_percent,
    )


def build_karaoke_srt_from_json(
    json_path,
    srt_path,
    max_line_width=25,
    max_line_count=1,
    silence_gap=0.35,
    comma_break_percent=70,
):
    """Legacy fallback when only faster-whisper segment JSON is available."""
    words = _flatten_words_from_json(json_path)
    return build_karaoke_srt_from_words(
        words,
        srt_path,
        max_line_width=max_line_width,
        max_line_count=max_line_count,
        silence_gap=silence_gap,
        comma_break_percent=comma_break_percent,
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

