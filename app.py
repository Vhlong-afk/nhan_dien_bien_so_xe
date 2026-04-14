from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
from detect import LicensePlateDetector
import base64
from pathlib import Path
import tempfile
import threading

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['VIDEO_TIMEOUT'] = 300  # 5 minutes timeout for video processing
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize detector once (model caching)
print("[APP] Initializing License Plate Detector...")
detector = LicensePlateDetector()
print("[APP] Detector ready!")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mkv'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_video(filename):
    """Check if file is video"""
    return filename.rsplit('.', 1)[1].lower() in {'mp4', 'avi', 'mov', 'mkv'}

def cleanup_file(filepath, delay=5):
    """Delete file after delay"""
    def remove():
        try:
            import time
            time.sleep(delay)
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"[CLEANUP] Deleted: {filepath}")
        except Exception as e:
            print(f"[CLEANUP ERROR] Failed to delete {filepath}: {str(e)}")
    
    thread = threading.Thread(target=remove, daemon=True)
    thread.start()

@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')

@app.route('/detect', methods=['POST'])
def detect():
    """Main detection endpoint"""
    print("[REQUEST] New detection request")
    
    #  VALIDATION
    if 'file' not in request.files:
        return jsonify({'error': '❌ Không có file được upload'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '❌ Chưa chọn file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'❌ Định dạng không hỗ trợ. Hỗ trợ: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    #  SAVE FILE
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        print(f"[UPLOAD] File saved: {filepath}")
        print(f"[UPLOAD] File size: {os.path.getsize(filepath)} bytes")
        
    except Exception as e:
        print(f"[ERROR] Upload failed: {str(e)}")
        return jsonify({'error': f'❌ Lỗi lưu file: {str(e)}'}), 500

    #  PROCESS
    try:
        if is_video(filename):
            print(f"[PROCESS] Video detected: {filename}")
            result = detector.process_video(filepath)
            cleanup_file(filepath, delay=2)
            return jsonify({'result': result, 'type': 'video'}), 200
        else:
            print(f"[PROCESS] Image detected: {filename}")
            img_b64, text, conf = detector.detect_license_plate(filepath)
            
            if img_b64:
                print(f"[SUCCESS] Detection complete - Text: {text}, Conf: {conf:.3f}")
                cleanup_file(filepath, delay=1)
                return jsonify({
                    'plate_image': img_b64,
                    'text': text,
                    'confidence': f'{conf:.2f}'
                }), 200
            else:
                print(f"[FAILED] {text}")
                cleanup_file(filepath, delay=1)
                return jsonify({'error': text}), 400
                
    except Exception as e:
        print(f"[CRASH] {str(e)}")
        import traceback
        traceback.print_exc()
        cleanup_file(filepath, delay=1)
        return jsonify({'error': f'❌ Lỗi server: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'detector': 'ready'}), 200

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({'error': '❌ File quá lớn (max 100MB)'}), 413

import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
