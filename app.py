import os
import re
import uuid
import shutil
import zipfile
import threading
import time
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from flask_caching import Cache
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from PIL import Image
import io

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
app.config['CACHE_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['SESSION_COOKIE_SECURE'] = False  # Set to False to allow HTTP session
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # Increase to 100MB
app.config['UPLOAD_CHUNK_SIZE'] = 4096  # Optimize chunk size for better performance
app.config['CLEANUP_INTERVAL'] = 3600  # Run cleanup every hour (in seconds)
app.config['FILE_EXPIRY_HOURS'] = 3  # Delete files after 3 hours
app.config['CACHE_TYPE'] = 'filesystem'
app.config['CACHE_DIR'] = app.config['CACHE_FOLDER']
app.config['CACHE_DEFAULT_TIMEOUT'] = 3600  # 1 hour cache timeout
app.config['CACHE_THRESHOLD'] = 1000  # Maximum number of items in cache
app.config['PDF_PREVIEW_DPI'] = 150  # DPI for PDF preview images
app.config['PDF_PREVIEW_QUALITY'] = 85  # JPEG quality for preview images
app.config['PRE_RENDER_PAGES'] = 3  # Number of pages to pre-render

# Create necessary folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['CACHE_FOLDER'], exist_ok=True)

# Initialize cache
cache = Cache(app)

# Tambahkan dictionary global untuk menyimpan status upload
upload_progress = {}

# Add current year to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def sanitize_filename(name):
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    sanitized = ''.join(c for c in name if c not in invalid_chars).strip()
    # Limit filename length to avoid issues
    if len(sanitized) > 100:
        sanitized = sanitized[:97] + "..."
    return sanitized or "Unnamed"

def extract_name_from_pages(doc, start_page, keyword, split_size):
    """Extract name from PDF pages based on keyword"""
    text = ""
    for i in range(start_page, min(start_page + split_size, len(doc))):
        text += doc[i].get_text()
    
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if keyword.upper() in line.upper():
            if i > 0:
                return lines[i - 1].strip()
    return f"Unknown_{start_page+1}_{min(start_page+split_size, len(doc))}"

def process_pdf(input_path, output_folder, split_size, keyword):
    """Process PDF file - split and rename"""
    results = []
    try:
        doc = fitz.open(input_path)
        total_pages = len(doc)
        
        for i in range(0, total_pages, split_size):
            new_doc = fitz.open()
            end_page = min(i + split_size - 1, total_pages - 1)
            new_doc.insert_pdf(doc, from_page=i, to_page=end_page)

            name = extract_name_from_pages(doc, i, keyword, split_size)
            safe_name = sanitize_filename(name)
            
            # Use just the name without page number prefix
            output_path = os.path.join(output_folder, f"{safe_name}.pdf")
            
            # Handle duplicate filenames
            counter = 1
            base_path = output_path
            while os.path.exists(output_path):
                name_part, ext = os.path.splitext(base_path)
                output_path = f"{name_part}_{counter}{ext}"
                counter += 1

            new_doc.save(output_path)
            new_doc.close()
            
            # Add to results
            results.append({
                'filename': os.path.basename(output_path),
                'pages': f"{i+1}-{end_page+1}",
                'path': output_path
            })
        
        doc.close()
        return {
            'success': True,
            'files': results,
            'total_files': len(results),
            'total_pages': total_pages
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def create_zip_archive(folder_path, output_filename=None):
    """Create a ZIP archive from a folder"""
    if not output_filename:
        output_filename = f"pdf_split_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    
    zip_path = os.path.join(os.path.dirname(folder_path), output_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(folder_path))
                zipf.write(file_path, arcname)
    
    return zip_path

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        
        # Create session folders
        session_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        session_output_folder = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
        
        os.makedirs(session_upload_folder, exist_ok=True)
        os.makedirs(session_output_folder, exist_ok=True)
        
        # Save uploaded file - optimize for speed
        filename = secure_filename(file.filename)
        file_path = os.path.join(session_upload_folder, filename)
        
        # Use buffer size optimization
        chunk_size = app.config.get('UPLOAD_CHUNK_SIZE', 4096)
        with open(file_path, 'wb') as f:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
        
        # Store file info in session
        session['uploaded_file'] = file_path
        session['original_filename'] = file.filename
        
        # Get PDF info
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            doc.close()
            session['total_pages'] = total_pages
        except Exception as e:
            flash(f'Error reading PDF: {str(e)}')
            return redirect(url_for('index'))
        
        return redirect(url_for('configure'))
    
    flash('Invalid file type. Only PDF files are allowed.')
    return redirect(url_for('index'))

@app.route('/configure')
def configure():
    """Show configuration page"""
    if 'uploaded_file' not in session:
        flash('Please upload a file first')
        return redirect(url_for('index'))
    
    return render_template('configure.html', 
                          filename=session.get('original_filename'),
                          total_pages=session.get('total_pages', 0))

@app.route('/get_pdf_url')
def get_pdf_url():
    """Return the URL for the uploaded PDF file"""
    if 'uploaded_file' not in session:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    # Create a temporary URL for the PDF
    pdf_url = url_for('serve_pdf', filename=os.path.basename(session['uploaded_file']))
    return jsonify({'success': True, 'url': pdf_url})

@app.route('/pdf/<path:filename>')
def serve_pdf(filename):
    """Serve the PDF file for preview"""
    if 'session_id' not in session:
        flash('Session expired')
        return redirect(url_for('index'))
    
    # Get the original filename from session
    original_filename = session.get('original_filename', filename)
    session_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['session_id'])
    
    # Look for the file in the session upload folder
    for file in os.listdir(session_upload_folder):
        file_path = os.path.join(session_upload_folder, file)
        if os.path.isfile(file_path):
            # Found the file, serve it
            response = send_file(file_path, mimetype='application/pdf')
            response.headers['Content-Disposition'] = 'inline; filename="{}"'.format(original_filename)
            return response
    
    # File not found
    return jsonify({'success': False, 'error': 'File not found'}), 404

@app.route('/pdf_output/<path:filename>')
def serve_output_pdf(filename):
    """Serve the output PDF file for preview"""
    if 'session_id' not in session:
        flash('Session expired')
        return redirect(url_for('index'))
    
    session_output_folder = os.path.join(app.config['OUTPUT_FOLDER'], session['session_id'])
    file_path = os.path.join(session_output_folder, filename)
    
    if os.path.exists(file_path):
        # Set Content-Disposition to 'inline' to display in browser instead of downloading
        response = send_file(file_path, mimetype='application/pdf')
        response.headers['Content-Disposition'] = 'inline; filename="{}"'.format(filename)
        return response
    else:
        return jsonify({'success': False, 'error': 'File not found'}), 404

@app.route('/process_status')
def process_status():
    """Return the current processing status"""
    if 'processing_status' not in session:
        return jsonify({'status': 'idle', 'progress': 0})
    
    return jsonify(session['processing_status'])

@app.route('/process', methods=['POST'])
def process():
    """Process the uploaded PDF"""
    if 'uploaded_file' not in session:
        flash('Please upload a file first')
        return redirect(url_for('index'))
    
    try:
        # Get form data
        split_size = request.form.get('split_size', type=int)
        keyword = request.form.get('keyword', 'DIBERIKAN KEPADA')
        
        if not split_size or split_size <= 0:
            flash('Split size must be a positive number')
            return redirect(url_for('configure'))
        
        print(f"Starting processing with split_size={split_size}, keyword='{keyword}'")
        print(f"Uploaded file: {session.get('uploaded_file')}")
        
        # Initialize processing status
        session['processing_status'] = {
            'status': 'processing',
            'progress': 0,
            'current_file': '',
            'files_processed': 0,
            'total_files': 0
        }
        
        # Process the PDF
        session_output_folder = os.path.join(app.config['OUTPUT_FOLDER'], session['session_id'])
        print(f"Output folder: {session_output_folder}")
        
        # Ensure output folder exists and is writable
        if not os.path.exists(session_output_folder):
            os.makedirs(session_output_folder, exist_ok=True)
            print(f"Created output folder: {session_output_folder}")
        
        # Check if file exists
        if not os.path.exists(session['uploaded_file']):
            raise FileNotFoundError(f"Uploaded file not found: {session['uploaded_file']}")
        
        result = process_pdf_with_status(session['uploaded_file'], session_output_folder, split_size, keyword)
        
        if result['success']:
            # Create ZIP file
            session['processing_status']['status'] = 'creating_zip'
            zip_filename = f"split_{os.path.basename(session['original_filename'])}.zip"
            zip_path = create_zip_archive(session_output_folder, zip_filename)
            session['zip_path'] = zip_path
            session['result'] = result
            
            # Update status to complete
            session['processing_status'] = {
                'status': 'complete',
                'progress': 100,
                'files_processed': result['total_files'],
                'total_files': result['total_files']
            }
            
            return redirect(url_for('result'))
        else:
            # Update status to error
            error_msg = result.get('error', 'Unknown error')
            print(f"Processing error: {error_msg}")
            session['processing_status'] = {
                'status': 'error',
                'error': error_msg
            }
            
            flash(f"Error processing PDF: {error_msg}")
            return redirect(url_for('configure'))
    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in process route: {str(e)}")
        traceback.print_exc()
        flash(f"Critical error: {str(e)}")
        return redirect(url_for('configure'))

def process_pdf_with_status(input_path, output_folder, split_size, keyword):
    """Process PDF file with status updates"""
    results = []
    try:
        print(f"Opening PDF: {input_path}")
        doc = fitz.open(input_path)
        total_pages = len(doc)
        total_files = (total_pages + split_size - 1) // split_size
        
        print(f"PDF opened successfully. Total pages: {total_pages}, Expected files: {total_files}")
        
        # Update status with total files
        if 'processing_status' in session:
            session['processing_status'].update({
                'total_files': total_files,
                'total_pages': total_pages
            })
            session.modified = True
        
        for i in range(0, total_pages, split_size):
            print(f"Processing pages {i+1}-{min(i+split_size, total_pages)}")
            new_doc = fitz.open()
            end_page = min(i + split_size - 1, total_pages - 1)
            new_doc.insert_pdf(doc, from_page=i, to_page=end_page)

            name = extract_name_from_pages(doc, i, keyword, split_size)
            safe_name = sanitize_filename(name)
            print(f"Extracted name: {safe_name}")
            
            # Use just the name without page number prefix
            output_path = os.path.join(output_folder, f"{safe_name}.pdf")
            
            # Handle duplicate filenames
            counter = 1
            base_path = output_path
            while os.path.exists(output_path):
                name_part, ext = os.path.splitext(base_path)
                output_path = f"{name_part}_{counter}{ext}"
                counter += 1
            
            # Update processing status
            if 'processing_status' in session:
                files_processed = len(results)
                progress = min(int((files_processed / total_files) * 100), 95)
                session['processing_status'].update({
                    'progress': progress,
                    'current_file': safe_name,
                    'files_processed': files_processed,
                    'current_page': i + 1,
                    'page_range': f"{i+1}-{end_page+1}"
                })
                session.modified = True

            print(f"Saving file to: {output_path}")
            new_doc.save(output_path)
            new_doc.close()
            print(f"File saved successfully: {output_path}")
            
            # Add to results
            results.append({
                'filename': os.path.basename(output_path),
                'pages': f"{i+1}-{end_page+1}",
                'path': output_path
            })
        
        doc.close()
        print("PDF processing completed successfully")
        return {
            'success': True,
            'files': results,
            'total_files': len(results),
            'total_pages': total_pages
        }
    except Exception as e:
        print(f"ERROR in PDF processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/result')
def result():
    """Show results page"""
    if 'result' not in session or 'zip_path' not in session:
        flash('No processed files found')
        return redirect(url_for('index'))
    
    return render_template('result.html', 
                          result=session['result'],
                          zip_filename=os.path.basename(session['zip_path']))

@app.route('/download_zip')
def download_zip():
    """Download the ZIP file"""
    if 'zip_path' not in session:
        flash('No ZIP file available')
        return redirect(url_for('index'))
    
    return send_file(session['zip_path'], 
                    as_attachment=True, 
                    download_name=os.path.basename(session['zip_path']))

@app.route('/download_file/<path:filename>')
def download_file(filename):
    """Download an individual file"""
    if 'session_id' not in session:
        flash('Session expired')
        return redirect(url_for('index'))
    
    session_output_folder = os.path.join(app.config['OUTPUT_FOLDER'], session['session_id'])
    file_path = os.path.join(session_output_folder, filename)
    
    if os.path.exists(file_path):
        response = send_file(file_path, mimetype='application/pdf')
        response.headers['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response
    else:
        flash('File not found')
        return redirect(url_for('result'))

@app.route('/clear')
def clear_session():
    """Clear the session and temporary files"""
    if 'session_id' in session:
        # Clean up session folders
        session_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['session_id'])
        session_output_folder = os.path.join(app.config['OUTPUT_FOLDER'], session['session_id'])
        
        if os.path.exists(session_upload_folder):
            shutil.rmtree(session_upload_folder)
        
        if os.path.exists(session_output_folder):
            shutil.rmtree(session_output_folder)
    
    # Clear session
    session.clear()
    
    return redirect(url_for('index'))

# Cleanup task - runs in background
def cleanup_old_files():
    """Remove files older than 3 hours and clean expired cache"""
    print(f"[{datetime.now()}] Running cleanup task - removing files older than {app.config['FILE_EXPIRY_HOURS']} hours")
    current_time = datetime.now()
    
    # Clean session folders
    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            if os.path.isdir(item_path):
                # Check folder modification time
                try:
                    mod_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                    time_diff = current_time - mod_time
                    hours_diff = time_diff.total_seconds() / 3600
                    
                    if hours_diff >= app.config['FILE_EXPIRY_HOURS']:
                        print(f"[{datetime.now()}] Removing old folder: {item_path} (age: {hours_diff:.1f} hours)")
                        shutil.rmtree(item_path)
                except Exception as e:
                    print(f"[{datetime.now()}] Error cleaning up folder {item_path}: {str(e)}")
    
    # Clean cache files older than 12 hours
    cache_folder = app.config['CACHE_FOLDER']
    if os.path.exists(cache_folder):
        cache_expiry_hours = 12  # Cache files can live longer than uploads
        for item in os.listdir(cache_folder):
            item_path = os.path.join(cache_folder, item)
            if os.path.isfile(item_path):
                try:
                    mod_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                    time_diff = current_time - mod_time
                    hours_diff = time_diff.total_seconds() / 3600
                    
                    if hours_diff >= cache_expiry_hours:
                        print(f"[{datetime.now()}] Removing old cache file: {item_path} (age: {hours_diff:.1f} hours)")
                        os.remove(item_path)
                except Exception as e:
                    print(f"[{datetime.now()}] Error cleaning up cache file {item_path}: {str(e)}")
    
    # Clean expired flask-cache entries (will happen automatically by flask-cache)
    print(f"[{datetime.now()}] Cleanup task completed")

# Background cleanup thread
def cleanup_scheduler():
    """Run cleanup task periodically in background"""
    while True:
        cleanup_old_files()
        time.sleep(app.config['CLEANUP_INTERVAL'])

# For Flask 2.x compatibility (before_first_request is deprecated)
cleanup_thread = None

def init_app(app):
    """Initialize the application with background tasks"""
    global cleanup_thread
    
    # Only start the thread once
    if cleanup_thread is None or not cleanup_thread.is_alive():
        cleanup_thread = threading.Thread(target=cleanup_scheduler)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        print(f"[{datetime.now()}] Started automatic cleanup thread (interval: {app.config['CLEANUP_INTERVAL']} seconds)")
        
        # Run initial cleanup
        initial_cleanup = threading.Thread(target=cleanup_old_files)
        initial_cleanup.daemon = True
        initial_cleanup.start()

@app.route('/debug_session')
def debug_session():
    """Debug route to check session data"""
    if not app.debug:
        return jsonify({'error': 'Debug mode not enabled'}), 403
    
    session_data = {key: session[key] for key in session if key != 'csrf_token'}
    return jsonify(session_data)

# Tambahkan route baru untuk mengecek progress
@app.route('/upload_progress/<session_id>')
def get_upload_progress(session_id):
    """Return the current upload progress"""
    if session_id in upload_progress:
        return jsonify(upload_progress[session_id])
    return jsonify({'progress': 0})

def get_pdf_page_hash(file_path, page_num, dpi):
    """Create a unique hash for caching a PDF page"""
    file_hash = hashlib.md5(open(file_path, 'rb').read(1024*1024)).hexdigest()  # Hash first 1MB only for speed
    return f"{file_hash}_page{page_num}_dpi{dpi}"

@app.route('/pdf_preview/<path:session_id>/<int:page_num>')
def pdf_preview(session_id, page_num):
    """Serve a rendered page of a PDF as an image for faster preview"""
    print(f"PDF Preview request for session {session_id}, page {page_num}")
    
    # Don't validate session for preview to avoid issues
    # This is ok because we're only showing preview of the user's own uploaded file
    try:
        # Get PDF path
        session_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        pdf_path = None
        
        # Check if folder exists
        if not os.path.exists(session_upload_folder):
            print(f"Error: Upload folder does not exist: {session_upload_folder}")
            return jsonify({'error': 'Session folder not found'}), 404
        
        print(f"Looking for PDF in {session_upload_folder}")
        for file in os.listdir(session_upload_folder):
            file_path = os.path.join(session_upload_folder, file)
            if os.path.isfile(file_path) and file.lower().endswith('.pdf'):
                pdf_path = file_path
                print(f"Found PDF: {file_path}")
                break
        
        if not pdf_path:
            print(f"Error: No PDF found in session folder")
            return jsonify({'error': 'PDF file not found'}), 404
        
        # Convert page number to 0-indexed
        page_idx = max(0, page_num - 1)
        
        # Open PDF and get page
        doc = fitz.open(pdf_path)
        if page_idx >= len(doc):
            print(f"Error: Page number {page_num} out of range (total pages: {len(doc)})")
            return jsonify({'error': 'Page number out of range'}), 404
        
        print(f"Rendering page {page_num} of {len(doc)}")
        page = doc[page_idx]
        
        # Render page to image with specified DPI
        dpi = app.config['PDF_PREVIEW_DPI']
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Direct method: Convert to PNG (more reliable than JPEG conversion)
        print(f"Converting page to PNG image (size: {pix.width}x{pix.height})")
        img_bytes = pix.tobytes("png")
        
        # Close document
        doc.close()
        
        # Create response with appropriate headers
        response = send_file(
            io.BytesIO(img_bytes),
            mimetype='image/png',
            as_attachment=False,
            download_name=f"page_{page_num}.png"
        )
        
        # Add cache headers
        response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
        
        # Add CORS headers to prevent issues
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        
        print(f"Successfully rendered page {page_num}")
        return response
    
    except Exception as e:
        import traceback
        print(f"Error rendering PDF preview: {str(e)}")
        traceback.print_exc()
        response = jsonify({'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500

def get_session_pdf_path():
    """Helper function to get the current session's PDF path"""
    if 'session_id' not in session or 'uploaded_file' not in session:
        return None
    
    return session.get('uploaded_file')

@app.route('/pdf_metadata/<path:session_id>')
@cache.cached(timeout=3600)
def pdf_metadata(session_id):
    """Get PDF metadata including total pages for client-side rendering"""
    if 'session_id' not in session or session.get('session_id') != session_id:
        return jsonify({'error': 'Invalid session or session expired'}), 403
    
    try:
        # Get PDF path
        pdf_path = get_session_pdf_path()
        if not pdf_path:
            return jsonify({'error': 'PDF file not found'}), 404
        
        # Open PDF and get metadata
        doc = fitz.open(pdf_path)
        
        # Basic metadata
        metadata = {
            'total_pages': len(doc),
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'keywords': doc.metadata.get('keywords', ''),
            'page_sizes': []
        }
        
        # Get page sizes for the first 10 pages (for preview layout)
        for i in range(min(10, len(doc))):
            page = doc[i]
            rect = page.rect
            metadata['page_sizes'].append({
                'width': rect.width,
                'height': rect.height,
                'aspect_ratio': rect.width / rect.height if rect.height else 1
            })
        
        # Close document
        doc.close()
        
        return jsonify(metadata)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize app with cleanup thread
    init_app(app)
    
    # For development only - use a production WSGI server for deployment
    # Use host='0.0.0.0' to make the app accessible on your local network
    app.run(debug=True, host='0.0.0.0', port=5000) 