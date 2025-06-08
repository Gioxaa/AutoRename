# PDF Splitter & Auto Renamer

A web application that splits PDF files and automatically renames them based on content.

## Features

- Upload PDF files via drag-and-drop interface
- Configure split size and keyword for name detection
- Preview PDFs before and after processing
- Download individual files or all files as a ZIP archive
- Automatic name extraction from PDF content

## Local Development

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python app.py
   ```
4. Access the application at http://127.0.0.1:5000

## Production Deployment

### Prerequisites

- A Linux VPS (Ubuntu/Debian recommended)
- A domain name pointing to your server
- SSH access to your server

### Deployment Steps

1. Copy all files to your server:
   ```
   scp -r * user@your-server:/path/to/deployment/
   ```

2. SSH into your server:
   ```
   ssh user@your-server
   ```

3. Navigate to the deployment directory:
   ```
   cd /path/to/deployment/
   ```

4. Make the deployment script executable:
   ```
   chmod +x deploy.sh
   ```

5. Run the deployment script:
   ```
   ./deploy.sh
   ```
   
6. Follow the prompts to enter your domain name.

The script will:
- Install necessary packages
- Set up a Python virtual environment
- Configure Nginx as a reverse proxy
- Set up HTTPS with Let's Encrypt
- Create a systemd service for the application

### Manual Deployment

If you prefer to deploy manually or the script doesn't work for your setup:

1. Install required packages:
   ```
   sudo apt update
   sudo apt install python3 python3-pip python3-venv nginx certbot python3-certbot-nginx
   ```

2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   pip install gunicorn
   ```

4. Configure Nginx:
   - Create a new site configuration in `/etc/nginx/sites-available/`
   - Enable the site with `sudo ln -s /etc/nginx/sites-available/your-config /etc/nginx/sites-enabled/`
   - Restart Nginx with `sudo systemctl restart nginx`

5. Set up SSL with Certbot:
   ```
   sudo certbot --nginx -d yourdomain.com
   ```

6. Create a systemd service for the application.

7. Enable and start the service:
   ```
   sudo systemctl enable pdfsplitter
   sudo systemctl start pdfsplitter
   ```

## Maintenance

- Check the application status:
  ```
  sudo systemctl status pdfsplitter
  ```

- View application logs:
  ```
  sudo journalctl -u pdfsplitter
  ```

- Restart the application:
  ```
  sudo systemctl restart pdfsplitter
  ```

- Renew SSL certificate (usually automatic):
  ```
  sudo certbot renew
  ```

## Requirements

- Python 3.7+
- Flask
- PyMuPDF (fitz)
- Other dependencies listed in requirements.txt

## Directory Structure

```
pdf-splitter-web/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
│   ├── base.html       # Base template with common elements
│   ├── index.html      # Home page with upload form
│   ├── configure.html  # Configuration page
│   └── result.html     # Results page with download options
├── uploads/            # Temporary storage for uploaded files
└── outputs/            # Temporary storage for processed files
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 