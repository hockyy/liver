"""Subtitle transcription engine."""
import os
import sys
import threading
import subprocess
from config import logger, SUBTITLE_REGEX, ASIAN_LANGUAGES
from utils import (
    clean_srt,
    fix_highlight_srt_gaps,
    build_karaoke_srt_from_json,
    oneword_srt_path,
    preserve_oneword_srt,
    prepare_karaoke_srt_from_oneword,
    rebuild_karaoke_from_captions_json,
    format_timestamp_from_match,
)


class SubtitleTranscriber:
    """Handles subtitle transcription using faster-whisper-xxl."""
    
    def __init__(self, model="large-v3", device="CUDA"):
        """
        Initialize the transcriber.
        
        Args:
            model: Whisper model to use
            device: Device to use for transcription (CUDA/CPU)
        """
        self.model = model
        self.device = device
        self.stop_flag = threading.Event()
        self.thread = None

    def transcribe_and_write_srt_live(self, audio_file, log_callback, options):
        """
        Transcribe audio file with options.
        
        Args:
            audio_file: Path to audio file
            log_callback: Callback function for logging
            options: Dictionary containing transcription options
                - lang: Language code
                - beam_size: Beam size for decoding
                - best_of: Best of parameter
                - vad_method: VAD method to use
                - vocal_extract: Voice extraction method (None, 'mdx1_kim2', 'mdx2_kim2', 'mb-roformer')
                - realign: Enable realignment
                - realign_device: Device for realignment
                - roformer_overlap: Overlap for roformer
                - roformer_vram: VRAM setting for roformer
                - diarize_method: Diarization method (None, 'pyannote_v3.0', etc.)
                - diarize_device: Device for diarization
                - num_speakers: Number of speakers (0 = auto)
                - min_speakers: Minimum number of speakers
                - max_speakers: Maximum number of speakers
                - word_timestamps: Enable word-level timestamps
                - highlight_words: Enable karaoke-style highlighting
                - one_word: One word per line setting (0, 1, 2)
                - sentence_split: Enable sentence splitting for line breaking
                - max_line_width: Max characters per subtitle line
                - max_line_count: Max lines per subtitle entry (1-4)
                - max_comma_cent: Break at comma after this % of line width
        """
        output_dir = os.path.dirname(audio_file)
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        lang = options.get('lang', '')
        cjk_srt_file = os.path.join(output_dir, f"{base_name}.srt")
        json_file = os.path.join(output_dir, f"{base_name}.json")
        captions_json_file = os.path.join(output_dir, f"{base_name}.captions.json")

        if os.path.exists(cjk_srt_file):
            if self._uses_karaoke_rebuild(options):
                log_callback(
                    "Rebuilding karaoke SRT from existing transcription.\n"
                )
                self._post_process_srt(cjk_srt_file, options, log_callback)
                return
            else:
                log_callback(f"Transcription already exists at {cjk_srt_file}\n")
                self._post_process_srt(cjk_srt_file, options, log_callback)
                return

        # Build command
        command = self._build_command(audio_file, output_dir, lang, options)

        log_callback(f"Starting transcription for {audio_file}\n")
        log_callback(f"Command: {self._format_command_for_display(command)}\n")

        try:
            # On Windows, create a new console window for faster-whisper with visible output
            creation_flags = 0
            startupinfo = None
            
            if sys.platform == 'win32':
                creation_flags = subprocess.CREATE_NEW_CONSOLE
                # Create startup info to ensure console is visible
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags = 0
            
            # Run without capturing output so it shows in the console
            process = subprocess.Popen(
                command,
                creationflags=creation_flags,
                startupinfo=startupinfo
            )
            
            log_callback(f"Process started (PID: {process.pid}). Check the console window for progress.\n")
            
            # Wait for completion
            return_code = process.wait()
            
            if return_code != 0:
                log_callback(f"Warning: Process exited with code {return_code}\n")
                
        except Exception as e:
            log_callback(f"Error starting transcription: {str(e)}\n")
            return

        # Post-process if transcription completed
        if self._uses_karaoke_rebuild(options):
            if os.path.exists(cjk_srt_file):
                log_callback(
                    "Transcription completed. Building karaoke SRT from per-word timings.\n"
                )
                self._post_process_srt(cjk_srt_file, options, log_callback)
            else:
                log_callback("Transcription failed or was stopped before completion.\n")
        elif os.path.exists(cjk_srt_file):
            log_callback(f"Transcription completed. SRT file saved at {cjk_srt_file}\n")
            self._post_process_srt(cjk_srt_file, options, log_callback)
        else:
            log_callback("Transcription failed or was stopped before completion.\n")

    def _uses_karaoke_rebuild(self, options):
        """Whether we build highlight SRT from JSON word timings ourselves."""
        return (
            options.get('highlight_words', False)
            and options.get('word_timestamps', True)
            and not options.get('realign', False)
            and not options.get('sentence_split', False)
        )

    def _post_process_srt(self, srt_file, options, log_callback):
        """Clean SRT output; build or fix karaoke highlight timing."""
        base_dir = os.path.dirname(srt_file)
        base_name = os.path.splitext(os.path.basename(srt_file))[0]
        json_file = os.path.join(base_dir, f"{base_name}.json")
        captions_json_file = os.path.join(base_dir, f"{base_name}.captions.json")
        oneword_srt_file = oneword_srt_path(srt_file)

        max_line_width = options.get('max_line_width', 25)
        max_line_count = options.get('max_line_count', 1)
        sentence_pause_ms = options.get('sentence_pause_ms', 350)
        split_on_punctuation = options.get('split_on_punctuation', True)

        try:
            if self._uses_karaoke_rebuild(options):
                built = False
                karaoke_opts = dict(
                    max_line_width=max_line_width,
                    max_line_count=max_line_count,
                    sentence_pause_ms=sentence_pause_ms,
                    split_on_punctuation=split_on_punctuation,
                    captions_json_path=captions_json_file,
                )

                if os.path.exists(srt_file):
                    try:
                        with open(srt_file, encoding='utf-8-sig') as handle:
                            sample = handle.read(4096)
                    except OSError:
                        sample = ''
                    if '<u>' not in sample:
                        preserve_oneword_srt(srt_file, oneword_srt_file)
                        log_callback(
                            f"Saved whisper one-word pass → {oneword_srt_file}\n"
                        )
                        built = prepare_karaoke_srt_from_oneword(
                            oneword_srt_file,
                            srt_file,
                            **karaoke_opts,
                        )

                if not built and os.path.exists(oneword_srt_file):
                    built = prepare_karaoke_srt_from_oneword(
                        oneword_srt_file,
                        srt_file,
                        **karaoke_opts,
                    )

                if not built and os.path.exists(captions_json_file):
                    built = rebuild_karaoke_from_captions_json(
                        captions_json_file,
                        srt_file,
                        max_line_width=max_line_width,
                        max_line_count=max_line_count,
                        sentence_pause_ms=sentence_pause_ms,
                        split_on_punctuation=split_on_punctuation,
                    )

                if not built and os.path.exists(json_file):
                    built = build_karaoke_srt_from_json(
                        json_file,
                        srt_file,
                        **karaoke_opts,
                    )

                if built:
                    log_callback(
                        f"Built karaoke SRT from per-word timings → {srt_file}\n"
                    )
                    if os.path.exists(captions_json_file):
                        log_callback(
                            f"Saved caption groups → {captions_json_file}\n"
                        )
                else:
                    log_callback(
                        "Warning: Could not build karaoke SRT from word timings\n"
                    )
            clean_srt(srt_file)
            log_callback(f"Cleaned {srt_file}\n")
            if options.get('highlight_words', False) and not (
                os.path.exists(captions_json_file) or os.path.exists(oneword_srt_file)
            ):
                if fix_highlight_srt_gaps(srt_file):
                    log_callback(
                        "Trimmed legacy highlight cues that spanned silence gaps\n"
                    )
        except Exception as e:
            log_callback(f"Note: Could not clean SRT file: {e}\n")

    def _comma_break_percent(self, options):
        """Map max_comma_cent setting to wrap scoring (100 = prefer not breaking at commas)."""
        value = options.get('max_comma_cent', '100 - Disabled')
        if isinstance(value, str):
            token = value.split()[0]
            try:
                return int(token)
            except ValueError:
                return 70
        return int(value)

    def _build_command(self, audio_file, output_dir, lang, options):
        """Build the faster-whisper-xxl command with all options."""
        karaoke_rebuild = self._uses_karaoke_rebuild(options)

        command = [
            'faster-whisper-xxl.exe', audio_file,
            '--model', self.model,
            '--device', self.device,
            '--compute_type', 'float32',  # Full precision for maximum accuracy
            '--output_dir', output_dir,
            '--output_format', 'srt',
            '--task', 'transcribe',
            '--beam_size', str(options.get('beam_size', 10)),
            '--best_of', str(options.get('best_of', 5)),
            '--verbose', 'true',
        ]
        
        # Add VAD settings (can be disabled with 'none')
        vad_method = options.get('vad_method', 'ten')
        if vad_method == 'none':
            command.extend(['--vad_filter', 'false'])
        else:
            command.extend(['--vad_filter', 'true', '--vad_method', vad_method])
            if 'vad_min_silence_duration_ms' in options:
                command.extend([
                    '--vad_min_silence_duration_ms',
                    str(options['vad_min_silence_duration_ms']),
                ])
            if 'vad_speech_pad_ms' in options:
                command.extend([
                    '--vad_speech_pad_ms',
                    str(options['vad_speech_pad_ms']),
                ])

        word_timestamps = options.get('word_timestamps', True)
        command.extend(['--word_timestamps', str(word_timestamps).lower()])

        if word_timestamps and options.get('hallucination_silence_threshold') is not None:
            command.extend([
                '--hallucination_silence_threshold',
                str(options['hallucination_silence_threshold']),
            ])

        realign = options.get('realign', False)
        sentence_split = options.get('sentence_split', False)
        highlight_words = options.get('highlight_words', False)

        one_word_setting = options.get('one_word', '0 - Disabled')
        if isinstance(one_word_setting, str):
            one_word_value = one_word_setting.split(' ')[0]
        else:
            one_word_value = str(one_word_setting)
        one_word_active = (
            word_timestamps
            and not realign
            and one_word_value != '0'
            and not karaoke_rebuild
        )

        # --standard / --standard_asia auto-enable --sentence, which disables karaoke.
        skip_standard_preset = (
            word_timestamps
            and not realign
            and (highlight_words or one_word_active or karaoke_rebuild)
            and not sentence_split
        )

        if not skip_standard_preset and not sentence_split:
            command.append('--standard_asia' if lang in ASIAN_LANGUAGES else '--standard')

        # Karaoke rebuild uses one-word-per-line SRT for tight timings, then we
        # assemble highlight captions ourselves.
        if karaoke_rebuild:
            command.extend(['--one_word', '2'])
        elif one_word_active:
            command.extend(['--one_word', one_word_value])
        
        # Add subtitle format settings (for brainrot/short-form content).
        # TikTok / lyrics karaoke skips these — we wrap words into lines ourselves.
        if sentence_split:
            command.append('--sentence')

        if not karaoke_rebuild:
            max_line_width = options.get('max_line_width', 1000)
            command.extend(['--max_line_width', str(max_line_width)])

            max_line_count = options.get('max_line_count', 1)
            command.extend(['--max_line_count', str(max_line_count)])

            max_comma_cent = options.get('max_comma_cent', '100 - Disabled')
            if sentence_split and max_comma_cent != '100 - Disabled':
                comma_value = max_comma_cent.split(' ')[0]
                command.extend(['--max_comma_cent', comma_value])

        # Add voice extraction if specified (PRO FEATURE)
        vocal_extract = options.get('vocal_extract')
        if vocal_extract and vocal_extract != 'none':
            command.extend(['--ff_vocal_extract', vocal_extract])
            
            # Add roformer-specific parameters for mb-roformer
            if vocal_extract == 'mb-roformer':
                command.extend(['--roformer_overlap', str(options.get('roformer_overlap', 0.25))])
                command.extend(['--roformer_vram', str(options.get('roformer_vram', 4))])
        
        # Add realignment if enabled (PRO FEATURE)
        if options.get('realign', False):
            command.append('--realign')
            realign_device = options.get('realign_device', 'automatic')
            if realign_device != 'automatic':
                command.extend(['--realign_device', realign_device])

        # Add diarization if enabled (PRO FEATURE - speaker separation)
        diarize_method = options.get('diarize_method', 'none')
        if diarize_method and diarize_method != 'none':
            command.extend(['--diarize', diarize_method])
            
            # Add diarize device
            diarize_device = options.get('diarize_device', 'cuda')
            command.extend(['--diarize_device', diarize_device])
            
            # Add speaker count options
            num_speakers = options.get('num_speakers', 0)
            if num_speakers > 0:
                command.extend(['--num_speakers', str(num_speakers)])
            else:
                # Use min/max speakers for auto-detection
                min_speakers = options.get('min_speakers', 1)
                max_speakers = options.get('max_speakers', 10)
                if min_speakers > 1:
                    command.extend(['--min_speakers', str(min_speakers)])
                if max_speakers < 10:
                    command.extend(['--max_speakers', str(max_speakers)])

        # Add language parameter only if the model is not cantonese
        if self.model != "cantonese":
            command.extend(['--language', lang])

        return command

    def _format_command_for_display(self, command):
        """Format command list for display with proper quoting."""
        formatted_parts = []
        for part in command:
            # Add quotes around parts that contain spaces or special characters
            if ' ' in part or any(char in part for char in ['(', ')', '&', '|', '<', '>']):
                formatted_parts.append(f'"{part}"')
            else:
                formatted_parts.append(part)
        return ' '.join(formatted_parts)

    def _process_output(self, process, tmp_file, log_callback):
        """Process transcription output and write to temporary file."""
        with open(tmp_file, 'w', encoding='utf-8') as cjk_f:
            segment_index = 1
            for line in process.stdout:
                if self.stop_flag.is_set():
                    process.terminate()
                    log_callback("Transcription stopped.\n")
                    return

                # Print to console for visibility (if running from terminal)
                print(line, end='', flush=True)

                if '-->' in line:
                    log_callback(line)
                    match = SUBTITLE_REGEX.match(line)
                    if match:
                        hours_start, minutes_seconds_start, hours_end, minutes_seconds_end, text = match.groups()
                        start_time = format_timestamp_from_match(hours_start, minutes_seconds_start)
                        end_time = format_timestamp_from_match(hours_end, minutes_seconds_end)
                        log_callback(f"{start_time} --> {end_time}\n")
                        cjk_f.write(f"{segment_index}\n{start_time} --> {end_time}\n{text.strip()}\n\n")
                        cjk_f.flush()
                        segment_index += 1

    def start_transcription(self, audio_file, log_callback, options):
        """
        Start transcription in a separate thread.
        
        Args:
            audio_file: Path to audio file
            log_callback: Callback function for logging
            options: Dictionary containing transcription options
        """
        if self.thread and self.thread.is_alive():
            log_callback("Transcription is already running.\n")
            return

        self.stop_flag.clear()
        self.thread = threading.Thread(
            target=self.transcribe_and_write_srt_live,
            args=(audio_file, log_callback, options)
        )
        self.thread.start()

    def stop_transcription(self):
        """Stop the current transcription."""
        if self.thread and self.thread.is_alive():
            self.stop_flag.set()
            self.thread.join()
        else:
            logger.info("No transcription process is running.")

