import fitz  # PyMuPDF
import os
import shutil
import json
import sys
from datetime import datetime
from tqdm import tqdm
import argparse
import logging
import re

# Setup logging
file_handler = logging.FileHandler("pdf_splitter.log")
file_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

logger = logging.getLogger("PDFSplitter")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

CONFIG_FILE = "pdf_splitter_config.json"

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

def sanitize_filename(name):
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    sanitized = ''.join(c for c in name if c not in invalid_chars).strip()
    # Limit filename length to avoid issues
    if len(sanitized) > 100:
        sanitized = sanitized[:97] + "..."
    return sanitized or "Unnamed"

def ask_overwrite_or_new_folder(path):
    """Handle existing output folder"""
    if os.path.exists(path):
        choice = input(f"📄 Folder '{path}' sudah ada. Replace? (y/n): ").strip().lower()
        if choice == 'y':
            shutil.rmtree(path)
            os.makedirs(path)
            logger.info(f"Replaced existing folder: {path}")
            return path
        elif choice == 'n':
            # Create sequential folder names (output, output_2, output_3, etc.)
            
            # Extract the base name without any numbers
            # For example: "output_2_2" -> "output"
            base_path = re.sub(r'(_\d+)+$', '', path)
            
            # Find next available number
            counter = 2
            while True:
                new_path = f"{base_path}_{counter}"
                if not os.path.exists(new_path):
                    break
                counter += 1
                
            os.makedirs(new_path)
            logger.info(f"Created new folder: {new_path}")
            return new_path
        else:
            print("Jawab dengan 'y' atau 'n'.")
            return ask_overwrite_or_new_folder(path)  # Recursively ask again
    
    # If path doesn't exist, create it
    os.makedirs(path)
    logger.info(f"Created folder: {path}")
    return path

def save_config(config):
    """Save current configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        logger.debug(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")

def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
    return {}

def process_pdf(input_path, output_folder, split_size, keyword):
    """Process PDF file - split and rename"""
    try:
        doc = fitz.open(input_path)
        total_pages = len(doc)
        
        logger.info(f"Processing PDF with {total_pages} pages")
        print(f"\n📄 Total pages: {total_pages}")
        print(f"🔢 Split size: {split_size} pages")
        print(f"🔍 Keyword: '{keyword}'")
        print("\nProcessing files...\n")
        
        # Process files with progress bar
        with tqdm(total=total_pages, desc="Progress", unit="page", ncols=100) as pbar:
            for i in range(0, total_pages, split_size):
                new_doc = fitz.open()
                end_page = min(i + split_size - 1, total_pages - 1)
                new_doc.insert_pdf(doc, from_page=i, to_page=end_page)

                name = extract_name_from_pages(doc, i, keyword, split_size)
                safe_name = sanitize_filename(name)
                
                # Use just the name without page number prefix
                output_path = os.path.join(output_folder, f"{safe_name}.pdf")

                new_doc.save(output_path)
                new_doc.close()
                
                # Log to file only
                logger.info(f"Created: {output_path} (Pages {i+1}-{end_page+1})")
                
                # Update progress bar
                pbar.update(min(split_size, total_pages - i))
                
                # Display file creation info
                file_info = f"{safe_name}.pdf (Pages {i+1}-{end_page+1})"
                tqdm.write(f"✅ {file_info}")
        
        doc.close()
        print(f"\n🎉 Selesai! Semua file disimpan di: {output_folder}")
        print(f"📊 Total file yang dibuat: {(total_pages + split_size - 1) // split_size}")
        
        # Open output folder for user convenience
        if sys.platform == 'win32':
            os.startfile(output_folder)
        elif sys.platform == 'darwin':  # macOS
            os.system(f'open "{output_folder}"')
        else:  # Linux
            os.system(f'xdg-open "{output_folder}"')
            
        return True
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        print(f"❌ Error: {e}")
        return False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="PDF Splitter & Auto Renamer")
    parser.add_argument("-i", "--input", help="Input PDF file path")
    parser.add_argument("-o", "--output", help="Output folder path")
    parser.add_argument("-s", "--split", type=int, help="Split size (pages)")
    parser.add_argument("-k", "--keyword", help="Keyword for name identification")
    return parser.parse_args()

def main():
    print("\n" + "="*40)
    print("🔥 PDF Splitter & Auto Renamer v2.0 🔥")
    print("="*40)

    # Load saved configuration
    config = load_config()
    
    # Parse command line arguments
    args = parse_arguments()

    try:
        # Get input path
        if args.input:
            input_path = args.input
        else:
            default_input = config.get('last_input', '')
            input_path = input(f"📂 Masukkan path file PDF {f'(Enter untuk: {default_input})' if default_input else ''}: ").strip('"')
            if not input_path and default_input:
                input_path = default_input
        
        if not os.path.exists(input_path):
            print("❌ File tidak ditemukan.")
            return
        
        # Get output folder
        if args.output:
            output_folder = args.output
        else:
            # Default output in the same directory as the script
            default_output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
            default_output = config.get('last_output', default_output)
            output_folder = input(f"📁 Output folder (Enter untuk default: {default_output}): ").strip()
            if not output_folder:
                output_folder = default_output
        
        output_folder = ask_overwrite_or_new_folder(output_folder)

        # Get split size - always ask for input unless provided as command line arg
        if args.split:
            split_size = args.split
        else:
            default_split = config.get('last_split_size', 2)
            split_input = input(f"🔢 Split per Page (angka > 0, default: {default_split}): ")
            
            # Use default if empty input
            if not split_input.strip():
                split_size = default_split
            else:
                try:
                    split_size = int(split_input)
                    if split_size <= 0:
                        print("⚠️ Harus lebih dari 0. Menggunakan default.")
                        split_size = default_split
                except ValueError:
                    print("⚠️ Input tidak valid. Menggunakan default.")
                    split_size = default_split

        # Get keyword
        default_keyword = config.get('last_keyword', "DIBERIKAN KEPADA")
        if args.keyword:
            keyword = args.keyword
        else:
            keyword = input(f"🔍 Kata kunci identifikasi nama (Enter untuk: {default_keyword}): ").strip()
            if not keyword:
                keyword = default_keyword

        # Save configuration for next run
        save_config({
            'last_input': input_path,
            'last_output': output_folder,
            'last_split_size': split_size,
            'last_keyword': keyword,
            'last_run': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        # Process the PDF
        process_pdf(input_path, output_folder, split_size, keyword)

    except KeyboardInterrupt:
        print("\n⛔ Program dibatalkan oleh user (Ctrl+C). Keluar...")
        logger.info("Program terminated by user")
        exit()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Unhandled exception: {e}", exc_info=True)

if __name__ == "__main__":
    main()
