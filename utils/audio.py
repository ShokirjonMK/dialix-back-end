import logging
import subprocess


def generate_waveform(input_path, output_path):
    cmd = [
        "audiowaveform",
        "-i",
        input_path,
        "-o",
        output_path,
        "--pixels-per-second",
        "30",
        "-b",
        "8",
    ]
    print(" ".join(cmd))
    waveform_process = subprocess.run(cmd, capture_output=True, text=True)
    if waveform_process.returncode != 0:
        raise Exception(
            "Waveform generation failed with code %d" % waveform_process.returncode,
            waveform_process.stderr,
        )


def get_audio_duration(local_path):
    duration = None

    try:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            local_path,
        ]
        result = subprocess.run(command, capture_output=True)
        logging.warning(f"result: {result}")
        if result.returncode == 0:
            # Parse the output to get the duration
            output = result.stdout.strip()
            duration = float(output)
    except Exception as e:
        logging.error(f"Error getting audio duration: {e}")

    return duration
