# main.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import json
import os
from auth import authenticate_token
from generate import generate_individual_pdf, generate_summary_pdf

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

@app.route('/api/generate/single', methods=['POST'])
@authenticate_token
def generate_single_pdf_route():
    base_path = os.path.dirname(os.path.abspath(__file__))
    input_pdf = os.path.join(base_path, 'templates', 'individuale.pdf')
    replacements = json.loads(request.form.get('replacements', '{}'))
    excel_file = request.files.get('excel')
    if not excel_file:
        return jsonify({"error": "Excel file is required"}), 400

    # Process the Excel file
    df = pd.read_excel(excel_file)
    list_replacements = df.to_dict('records')
    # replace nan values with empty string
    for data in list_replacements:
        for key, value in data.items():
            if pd.isna(value):
                data[key] = ''
    print('list_replacements', list_replacements)

    return generate_individual_pdf(input_pdf, replacements, list_replacements)

@app.route('/api/generate/multiple', methods=['POST'])
@authenticate_token
def generate_multiple_pdf_route():
    base_path = os.path.dirname(os.path.abspath(__file__))
    input_pdf = os.path.join(base_path, 'templates', 'riepilogativo.pdf')
    replacements = json.loads(request.form.get('replacements', '{}'))
    excel_file = request.files.get('excel')
    if not excel_file:
        return jsonify({"error": "Excel file is required"}), 400

    # Process the Excel file
    df = pd.read_excel(excel_file)
    list_replacements = df.to_dict('records')
    # replace nan values with empty string
    for data in list_replacements:
        for key, value in data.items():
            if pd.isna(value):
                data[key] = ''
    print('list_replacements', list_replacements)

    return generate_summary_pdf(input_pdf, 6, 13, 8, replacements, list_replacements)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)