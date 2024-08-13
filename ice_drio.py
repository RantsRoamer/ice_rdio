import json
import os
import requests
from pydub import AudioSegment
from pydub.silence import detect_silence
from datetime import datetime
import tempfile
import logging
import io
import argparse
import time

def configure_logging(config):
    # Create log filename with current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_filename = os.path.join(config['log_dir'], f"ice_rdio-{date_str}.log")
    
    # Configure logging to file
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Keep output on console for immediate feedback
        ]
    )

# Load configuration
def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def process_audio(buffer, config, debug=False):
    try:
        buffer.seek(0)  # Ensure to read from the start
        # Process the buffer into an audio segment
        audio_segment = AudioSegment.from_file(buffer, format="mp3")

        # Check audio level
        loudness = audio_segment.dBFS
        if debug:
            logging.info(f"Current loudness: {loudness:.2f} dBFS")

        return audio_segment if loudness > config['audio']['threshold'] else None
    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        return None

def trim_leading_silence(audio_segment, silence_thresh=-40.0, chunk_size=10):
    """
    Trims leading silence from an AudioSegment.
    
    :param audio_segment: The audio segment to trim.
    :param silence_thresh: The silence threshold in dBFS. Audio quieter than this will be considered silence.
    :param chunk_size: The chunk size (in ms) to use when checking for silence.
    :return: The trimmed audio segment.
    """
    silent_ranges = detect_silence(audio_segment, min_silence_len=chunk_size, silence_thresh=silence_thresh)
    if silent_ranges:
        start_silence_end = silent_ranges[0][1]  # End of the first silence range
        return audio_segment[start_silence_end:]  # Trim leading silence
    return audio_segment

def capture_audio(config, debug=False):
    while True:
        try:
            logging.info("Attempting to connect to IceCast stream...")
            response = requests.get(
                config['icecast']['url'], 
                stream=True, 
                auth=(config['icecast']['username'], config['icecast']['password']), 
                timeout=10
            )
            
            if response.status_code == 200:
                logging.info("Connected to IceCast stream.")
                
                # Persistent buffer for accumulating audio data
                buffer = io.BytesIO()
                current_recording = AudioSegment.empty()
                recording_started = False
                temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                logging.info(f"Using temporary file {temp_audio_file.name} for audio capture.")

                # Read stream in larger chunks
                for chunk in response.iter_content(chunk_size=32768):  # Further increased chunk size
                    buffer.write(chunk)
                    
                    # Only attempt to process if we have enough data
                    if buffer.tell() >= 65536:  # Further increase to ensure complete audio segments
                        audio_segment = process_audio(buffer, config, debug)

                        if audio_segment:
                            if not recording_started:
                                recording_started = True
                                logging.info("Audio detected, starting recording...")

                            # Append audio segment to current recording
                            current_recording += audio_segment

                        elif recording_started:
                            logging.info("Audio level dropped below threshold, stopping recording.")
                            # Trim leading silence
                            trimmed_audio = trim_leading_silence(current_recording, silence_thresh=config['audio']['threshold'])
                            # Export the accumulated audio to the temporary file
                            trimmed_audio.export(temp_audio_file.name, format="wav")
                            logging.info(f"Audio file {temp_audio_file.name} created, preparing for upload.")
                            process_audio_file(temp_audio_file.name, config)
                            recording_started = False
                            current_recording = AudioSegment.empty()  # Reset recording
                            temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                            logging.info(f"Using new temporary file {temp_audio_file.name} for audio capture.")

                        buffer = io.BytesIO()  # Reset buffer for next segment
            else:
                logging.error(f"Failed to connect to IceCast stream: {response.status_code}")
                break  # Exit the loop if connection fails due to server response

        except requests.exceptions.RequestException as e:
            logging.error(f"Connection error: {e}. Attempting to reconnect in 5 seconds...")
            time.sleep(5)  # Wait before attempting to reconnect
        except Exception as e:
            logging.error(f"An error occurred: {e}")

def process_audio_file(audio_file_path, config):
    try:
        if os.path.exists(audio_file_path):
            logging.info(f"Audio file {audio_file_path} exists. Proceeding with upload.")
            # Upload to Rdio Scanner
            upload_to_rdio_scanner(audio_file_path, config)
        else:
            logging.error(f"Audio file {audio_file_path} does not exist.")
    except Exception as e:
        logging.error(f"Error processing audio file: {e}")
    finally:
        # Remove the temporary audio file
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)

def upload_to_rdio_scanner(audio_file, config):
    try:
        with open(audio_file, 'rb') as af:
            timestamp = datetime.utcnow().isoformat() + 'Z'
            files = {
                'audio': (audio_file, af),
                'audioName': audio_file,
                'audioType': 'audio/x-wav',
                'dateTime': timestamp,
                'frequency': config['rdio_scanner']['frequency'],
                'key': config['rdio_scanner']['api_key'],
                'source': config['rdio_scanner']['source'],
                'system': config['rdio_scanner']['system'],
                'systemLabel': config['rdio_scanner']['system_label'],
                'talkgroup': config['rdio_scanner']['talkgroup'],
                'talkgroupGroup': config['rdio_scanner']['talkgroup_group'],
                'talkgroupLabel': config['rdio_scanner']['talkgroup_label'],
                'talkgroupTag': config['rdio_scanner']['talkgroup_tag'],
            }

            logging.info(f"Uploading audio file {audio_file} to Rdio Scanner...")
            response = requests.post(config['rdio_scanner']['url'], files=files)
            if response.status_code == 200:
                logging.info("Audio uploaded successfully.")
            else:
                logging.error("Failed to upload audio: %s", response.text)
    except Exception as e:
        logging.error(f"Error uploading audio: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IceCast to Rdio Scanner audio processor.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode to show current loudness")
    args = parser.parse_args()

    config = load_config()
    configure_logging(config)  # Set up logging
    capture_audio(config, debug=args.debug)
