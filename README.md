# Audio Noise Reducer

A web-based application that reduces background noise from audio files using spectral noise reduction techniques. The application provides a user-friendly interface for uploading audio files, adjusting noise reduction parameters, and downloading the processed results.

## Features

- Upload audio files in multiple formats (WAV, MP3, OGG, FLAC, M4A)
- Adjustable noise reduction strength (0.1 - 6.0)
- Real-time processing progress indication
- Audio preview player with playback controls
- Multiple output format options (WAV, MP3, OGG, FLAC)
- Download processed audio files

## Prerequisites

- Python 3.7+
- FFmpeg installed on the system
- Web browser with HTML5 audio support

## Installation

1. Clone the repository: 
git clone [https://github.com/arvind-git-code/noise_remover-webapp.git](https://github.com/arvind-git-code/noise_remover-webapp.git)
cd audio-noise-reducer

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required Python packages:
```bash
pip install -r requirements.txt
```

4. Install FFmpeg:
- **Ubuntu/Debian**:
  ```bash
  sudo apt-get update
  sudo apt-get install ffmpeg
  ```
- **Windows**: Download from [FFmpeg website](https://ffmpeg.org/download.html)
- **macOS**:
  ```bash
  brew install ffmpeg
  ```

## Configuration

1. Create an `uploads` directory in the project root:
```bash
mkdir uploads
```

2. (Optional) Adjust the following settings in `app.py`:
- `MAX_CONTENT_LENGTH`: Maximum upload file size (default: 500MB)
- `SECRET_KEY`: Flask application secret key
- Server host and port in `app.run()`

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open a web browser and navigate to:
```
http://localhost:5000
```

3. Using the application:
   - Click "Choose File" to select an audio file
   - Adjust the noise reduction strength slider (higher values = stronger reduction)
   - Select desired output format
   - Click "Process Audio" to start noise reduction
   - Wait for processing to complete
   - Preview the processed audio using the built-in player
   - Click "Download" to save the processed file

## Technical Details

### Noise Reduction Algorithm

The application uses the Short-Time Fourier Transform (STFT) for spectral noise reduction:
1. Converts audio to frequency domain using STFT
2. Estimates noise profile from the first few frames
3. Creates and applies a spectral subtraction mask
4. Smooths the mask using median filtering
5. Converts back to time domain using inverse STFT

### File Processing

- Input files are automatically converted to WAV format for processing
- Supports mono and stereo audio (stereo is converted to mono)
- Audio is normalized before processing
- Processed files are converted to the selected output format using FFmpeg

## API Endpoints

- `GET /`: Main application interface
- `POST /upload`: Upload and process audio file
- `GET /status/<task_id>`: Get processing status
- `GET /download/<task_id>`: Download processed file

## Error Handling

- Invalid file types are rejected
- Processing errors are displayed in the UI
- Failed tasks are automatically cleaned up
- Temporary files are removed after processing

## Security Features

- Secure filename handling
- File type validation
- Maximum file size limit
- CORS support for API access

## Browser Compatibility

Tested and supported on:
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Known Limitations

- Large files may take significant time to process
- Processing is CPU-intensive
- Memory usage scales with file size
- Browser audio preview may not support all formats

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Add your license information here]

## Acknowledgments

- FFmpeg for audio format conversion
- SciPy for signal processing
- Flask for web framework

