from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import numpy as np
import soundfile as sf
from scipy import signal
import subprocess
import uuid
import threading
from pathlib import Path
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure upload folder and settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'flac', 'm4a'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Create uploads directory if it doesn't exist
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

# Store processing status
processing_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def reduce_noise(audio_data, strength=1.0):
    # Parameters for STFT
    nperseg = 2048
    noverlap = nperseg // 2
    
    # Compute STFT
    f, t, Zxx = signal.stft(audio_data, fs=44100, nperseg=nperseg, noverlap=noverlap,
                           boundary='zeros', padded=True)
    
    # Get magnitude and phase
    magnitude = np.abs(Zxx)
    phase = np.angle(Zxx)
    
    # Add small constant to prevent division by zero
    eps = np.finfo(magnitude.dtype).eps
    
    # Estimate noise profile
    noise_profile = np.mean(magnitude[:, :10], axis=1)
    
    # Compute mask
    mask = (magnitude - noise_profile.reshape(-1, 1) * strength) / (magnitude + eps)
    mask = np.maximum(0, mask)
    mask = np.minimum(1, mask)
    
    # Smooth the mask
    smoothed_mask = signal.medfilt2d(mask, kernel_size=(3, 3))
    
    # Apply the mask
    Zxx_denoised = Zxx * smoothed_mask
    
    # Inverse STFT
    _, denoised_audio = signal.istft(Zxx_denoised, fs=44100, nperseg=nperseg,
                                   noverlap=noverlap, boundary=True)
    
    return denoised_audio

def process_audio(input_path, output_path, output_format, strength, task_id):
    try:
        processing_status[task_id]['status'] = 'Converting input...'
        processing_status[task_id]['progress'] = 10
        
        # Convert input to WAV if needed
        temp_wav = None
        if not input_path.lower().endswith('.wav'):
            temp_wav = f"{input_path}_temp.wav"
            try:
                subprocess.run([
                    'ffmpeg', '-i', input_path,
                    '-acodec', 'pcm_s16le',
                    '-ar', '44100',
                    '-y', temp_wav
                ], check=True, capture_output=True, text=True)
                input_path = temp_wav
            except subprocess.CalledProcessError as e:
                raise Exception(f"FFmpeg error: {e.stderr}")
        
        processing_status[task_id]['status'] = 'Loading audio...'
        processing_status[task_id]['progress'] = 20
        
        # Load and process audio
        try:
            audio_data, sample_rate = sf.read(input_path)
        except Exception as e:
            raise Exception(f"Error reading audio file: {str(e)}")
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Normalize input
        audio_data = audio_data.astype(np.float32)
        if audio_data.max() > 1.0 or audio_data.min() < -1.0:
            audio_data = audio_data / np.max(np.abs(audio_data))
        
        processing_status[task_id]['status'] = 'Reducing noise...'
        processing_status[task_id]['progress'] = 40
        
        # Apply noise reduction
        try:
            denoised_audio = reduce_noise(audio_data, float(strength))
        except Exception as e:
            raise Exception(f"Error during noise reduction: {str(e)}")
        
        processing_status[task_id]['progress'] = 80
        
        # Save to temporary WAV
        temp_output = f"{output_path}_temp.wav"
        try:
            sf.write(temp_output, denoised_audio, sample_rate)
        except Exception as e:
            raise Exception(f"Error saving temporary file: {str(e)}")
        
        # Convert to desired format
        processing_status[task_id]['status'] = 'Converting to final format...'
        if output_format.upper() != 'WAV':
            try:
                subprocess.run([
                    'ffmpeg', '-i', temp_output,
                    '-y', output_path
                ], check=True, capture_output=True, text=True)
                os.remove(temp_output)
            except subprocess.CalledProcessError as e:
                raise Exception(f"Error converting to {output_format}: {e.stderr}")
        else:
            os.rename(temp_output, output_path)
        
        # Clean up
        if temp_wav and os.path.exists(temp_wav):
            os.remove(temp_wav)
        
        processing_status[task_id]['status'] = 'Complete'
        processing_status[task_id]['progress'] = 100
        processing_status[task_id]['result'] = output_path
        
    except Exception as e:
        processing_status[task_id]['status'] = f'Error: {str(e)}'
        processing_status[task_id]['error'] = True
        # Clean up any temporary files
        for temp_file in [temp_wav, temp_output]:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        logger.debug("Upload request received")
        
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        
        if not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Generate unique ID for this task
        task_id = str(uuid.uuid4())
        logger.debug(f"Created task ID: {task_id}")
        
        try:
            # Create task directory
            task_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)
            os.makedirs(task_dir, exist_ok=True)
            
            # Save uploaded file
            filename = secure_filename(file.filename)
            input_path = os.path.join(task_dir, f"input_{filename}")
            file.save(input_path)
            logger.debug(f"File saved to: {input_path}")
            
            # Verify file was saved
            if not os.path.exists(input_path):
                raise Exception("File was not saved successfully")
            
            # Get parameters
            strength = request.form.get('strength', '1.0')
            output_format = request.form.get('format', 'wav')
            
            # Prepare output path
            output_filename = f"output.{output_format.lower()}"
            output_path = os.path.join(task_dir, output_filename)
            
            # Initialize status
            processing_status[task_id] = {
                'status': 'Starting...',
                'progress': 0,
                'error': False,
                'input_path': input_path,
                'output_path': output_path
            }
            
            # Start processing in background
            thread = threading.Thread(
                target=process_audio,
                args=(input_path, output_path, output_format, strength, task_id)
            )
            thread.daemon = True  # Make thread daemon
            thread.start()
            
            logger.debug(f"Processing started for task: {task_id}")
            return jsonify({'task_id': task_id})
            
        except Exception as e:
            logger.error(f"Error during file processing: {str(e)}")
            # Clean up if there was an error
            if task_id in processing_status:
                del processing_status[task_id]
            if 'task_dir' in locals() and os.path.exists(task_dir):
                try:
                    import shutil
                    shutil.rmtree(task_dir)
                except:
                    pass
            raise
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/status/<task_id>')
def get_status(task_id):
    try:
        if task_id not in processing_status:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(processing_status[task_id])
    except Exception as e:
        logger.error(f"Status error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<task_id>')
def download_file(task_id):
    try:
        if task_id not in processing_status:
            return "Task not found", 404
        
        status = processing_status[task_id]
        if 'result' not in status:
            return "File not ready", 404
        
        if not os.path.exists(status['result']):
            return "File not found", 404

        # Check if this is a range request (for audio preview)
        if 'Range' in request.headers:
            return send_file(
                status['result'],
                mimetype='audio/wav',  # Adjust mimetype based on actual format
                conditional=True  # Enable partial content support
            )
        else:
            # For direct downloads, force download with original filename
            filename = os.path.basename(status['result'])
            return send_file(
                status['result'],
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return str(e), 500

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST')
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)