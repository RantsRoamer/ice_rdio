
# Ice-Rdio

Ice-Rdio is an audio streaming application that captures audio from an IceCast server, processes it to detect audio levels, trims leading silence, and uploads the audio to an Rdio Scanner server. This application is designed to run on Linux and can be configured to run as a background service.

## Features

- Connects to an IceCast server to capture streaming audio.
- Detects audio levels and records only when audio exceeds a specified threshold.
- Trims leading silence from audio recordings.
- Uploads processed audio files to an Rdio Scanner server.
- Logs activity to a file with a configurable log directory.

## Prerequisites

- Python 3.6 or later
- FFmpeg (required by `pydub` for audio processing)
- Python packages: `requests`, `pydub`

## Installation

1. **Install FFmpeg**

   You need to have FFmpeg installed on your system. You can install it using the following command:

   ```bash
   sudo apt-get update
   sudo apt-get install ffmpeg
   ```

2. **Clone the Repository**

   ```bash
   git clone https://github.com/your-username/ice-rdio.git
   cd ice-rdio
   ```

3. **Install Python Dependencies**

   Create a virtual environment and install the required packages:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure the Application**

   Edit the `config.json` file to specify your IceCast server details, Rdio Scanner API details, and logging directory:

   ```json
   {
     "icecast": {
       "url": "http://your-icecast-server-url/stream",
       "username": "your-username",
       "password": "your-password"
     },
     "audio": {
       "threshold": -20
     },
     "rdio_scanner": {
       "url": "https://other-rdio-scanner.example.com/api/call-upload",
       "api_key": "d2079382-07df-4aa9-8940-8fb9e4ef5f2e",
       "frequency": 774031250,
       "source": 4424000,
       "system": 11,
       "systemLabel": "RSP25MTL",
       "talkgroup": 54241,
       "talkgroupGroup": "Fire",
       "talkgroupLabel": "TDB A1",
       "talkgroupTag": "Fire dispatch"
     },
     "log_dir": "/path/to/logs/"
   }
   ```

## Usage

Run the application with the following command:

```bash
python ice_rdio.py --debug
```

### Running as a Background Service

To run Ice-Rdio as a background service, you can use `nohup` or create a `systemd` service.

#### Using `nohup`

Run the following command to start the application in the background:

```bash
nohup python ice_rdio.py &> /dev/null &
```

#### Creating a `systemd` Service

1. **Create the `systemd` service file** `/etc/systemd/system/ice_rdio.service`:

   ```ini
   [Unit]
   Description=IceCast to Rdio Scanner Audio Processor
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 /path/to/ice_rdio.py
   WorkingDirectory=/path/to/ice-rdio
   Restart=always
   User=your-username
   Group=your-group
   Environment="PATH=/path/to/ice-rdio/venv/bin"

   [Install]
   WantedBy=multi-user.target
   ```

   Replace `/path/to/ice-rdio` with the actual path to your application and adjust `User` and `Group` to match your system's user and group.

2. **Enable and start the service**:

   ```bash
   sudo systemctl enable ice_rdio
   sudo systemctl start ice_rdio
   ```

3. **Check the status of the service**:

   ```bash
   sudo systemctl status ice_rdio
   ```

## Logs

Logs are stored in the directory specified in the `config.json` file under `log_dir`. Each log file is named with the prefix `ice_rdio-` followed by the date.

## License

This project is licensed under the MIT License.
