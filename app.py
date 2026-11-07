import os
import json
from dotenv import load_dotenv
from sarvamai import SarvamAI
from pypdf import PdfReader
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy

load_dotenv()
client = SarvamAI(api_subscription_key=os.environ.get("SARVAM_API_KEY"))

app = Flask(__name__)

# 1. Configure the Real Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///erp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. Define your Database Table
class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False)
    vendor = db.Column(db.String(100), nullable=False)
    approved_amount = db.Column(db.Float, nullable=False)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def process_invoice():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    reader = PdfReader(file)
    invoice_text = "".join(page.extract_text() + "\n" for page in reader.pages)

    # Extract data using Sarvam AI
    response = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[
            {"role": "system", "content": "You are an Accounts Payable assistant. Extract the Vendor, Invoice Number, PO Number, and Total Due from the text. Output ONLY a valid JSON object without markdown tags."},
            {"role": "user", "content": invoice_text}
        ]
    )
    
    clean_text = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    
    try:
        ai_data = json.loads(clean_text)
        po_number = ai_data.get("PO Number")
        total_due = float(ai_data.get("Total Due", "$0").replace("$", "").replace(",", ""))
        vendor = ai_data.get("Vendor")
        
        # 3. Query the REAL Database
        po_record = PurchaseOrder.query.filter_by(po_number=po_number).first()
        
        if not po_record:
            status = "❌ REJECTED"
            message = f"PO Number {po_number} not found in database."
            action = "Requires manual review."
        elif po_record.vendor.lower() != vendor.lower() or po_record.approved_amount != total_due:
            status = "⚠️ FLAGGED"
            message = "Mismatch in vendor name or approved amount."
            action = f"System expected {po_record.vendor} for ${po_record.approved_amount}."
        else:
            status = "✅ APPROVED"
            message = f"Invoice perfectly matches {po_number}."
            action = f"Triggering ERP payment for ${total_due} to {vendor}."

        return jsonify({
            "status": status, "message": message, "action": action,
            "extracted_data": ai_data
        })
    except Exception as e:
        return jsonify({"error": f"Failed to parse AI output: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)