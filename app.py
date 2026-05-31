from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import os
import starmaker_scraper

app = Flask(__name__)
CORS(app) # Allow cross-origin requests from the Next.js frontend

# Ensure templates and static directories exist
os.makedirs('templates', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('downloads', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    
    if not url or 'starmaker' not in url.lower():
        return jsonify({"success": False, "error": "Please provide a valid StarMaker URL"}), 400
        
    try:
        # Run scraper
        result = starmaker_scraper.scrape_starmaker(url)
        
        if result and result.get('success'):
            return jsonify({
                "success": True, 
                "filename": result['filename'],
                "filepath": result['filepath']
            })
        else:
            return jsonify({
                "success": False, 
                "error": result.get('error', 'Failed to find media URL')
            }), 400
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/serve/<path:filename>')
def serve_file(filename):
    filepath = os.path.join('downloads', filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
