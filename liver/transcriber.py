"""Subtitle transcription engine."""
import os
import sys
import threading
import subprocess
from config import logger, SUBTITLE_REGEX, ASIAN_LANGUAGES
from utils import clean_srt, format_timestamp_from_match


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
        """
        output_dir = os.path.dirname(audio_file)
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        lang = options.get('lang', '')
        cjk_srt_file = os.path.join(output_dir, f"{base_name}.srt")

        if os.path.exists(cjk_srt_file):
            log_callback(f"Transcription already exists at {cjk_srt_file}\n")
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
        if os.path.exists(cjk_srt_file):
            log_callback(f"Transcription completed. SRT file saved at {cjk_srt_file}\n")
            try:
                clean_srt(cjk_srt_file)
                log_callback(f"Cleaned {cjk_srt_file}\n")
            except Exception as e:
                log_callback(f"Note: Could not clean SRT file: {e}\n")
        else:
            log_callback("Transcription failed or was stopped before completion.\n")

    def _build_command(self, audio_file, output_dir, lang, options):
        """Build the faster-whisper-xxl command with all options."""
        command = [
            'faster-whisper-xxl.exe', audio_file,
            '--model', self.model,
            '--device', self.device,
            '--output_dir', output_dir,
            '--output_format', 'srt',
            '--task', 'transcribe',
            '--beam_size', str(options.get('beam_size', 10)),
            '--best_of', str(options.get('best_of', 5)),
            '--verbose', 'true',
            '--vad_filter', 'true',
            '--vad_method', options.get('vad_method', 'ten'),
            '--standard_asia' if lang in ASIAN_LANGUAGES else '--standard',
        ]

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

