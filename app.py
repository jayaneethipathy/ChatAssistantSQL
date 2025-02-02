import sqlite3
import logging
from flask import Flask, request, jsonify, render_template
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

import torch
import pandas as pd
# Initialize Flask app
app = Flask(__name__)


model_name = "mrm8488/sqlova-large"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
MAX_INPUT_LENGTH = 256
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# SQL execution function
def execute_query(query, params=()):
    try:
        with sqlite3.connect('employee_database.db') as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            return result, columns
    except sqlite3.Error as e:
        logging.error(f"SQL Error: {str(e)}")
        return str(e), []

# Hugging Face Text-to-SQL conversion function
def generate_sql_query(natural_query):
    # Prefix with instruction for T5 model
    input_text = "Text to SQL: " + natural_query
    inputs = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True)

    # Ensure to use the right device (GPU if available)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    inputs = {key: value.to(device) for key, value in inputs.items()}
    
    # Generate SQL from the model
    with torch.no_grad():
        outputs = model.generate(**inputs, max_length=512)  # Keep max_length for generation
    
    sql_query = tokenizer.decode(outputs[0], skip_special_tokens=True)
    sql_query = sql_query.replace("SQL:", "").strip()
    return sql_query

# Data processing function to format SQL query results into HTML
def process_data(result, intent, columns):
    if result is None:
        logging.error("No data returned from the query.")
        return "<p>No results found.</p>"

    if isinstance(result, str):  # Check if result is an error message
        logging.error(f"SQL Error: {result}")
        return f"<p>Database Error: {result}</p>"
    try:
        # Create DataFrame for results
        
        df = pd.DataFrame(result, columns=columns)
        logging.info(f"DataFrame created with columns: {columns}")
        if df.empty:
            return "<p>No results found.</p>" 
        
        if intent == "salary_query":
            if not df.empty:
                df['Salary'] = pd.to_numeric(df['Salary'], errors='coerce')
                total_salary = df['Salary'].sum()
                logging.info(f"Total Salary: {total_salary}")
                return f"<p>Total Salary: {total_salary}</p>"
            else:
                return "<p>No salary data found for the given criteria.</p>"
        elif intent == "employee_details_query":
            if not df.empty:
                employee_details = df.iloc[0].to_dict()
                html_output = "<ul>"
                for key, value in employee_details.items():
                    html_output += f"<li><b>{key}:</b> {value}</li>"
                html_output += "</ul>"
                return html_output
            else:
                return "<p>No employee details found for the given criteria.</p>"
        elif intent == "employee_query":
            if not df.empty:
                return df.to_html(classes='table table-striped', index=False)
            else:
                return "<p>No employees found for the given criteria.</p>"
        elif intent == "manager_query":
            if not df.empty:
                manager = df['Manager'].iloc[0]
                return f"<p>The manager is: {manager}</p>"
            else:
                return "<p>No manager found for the given criteria.</p>"
        else:
            return "<p>Invalid intent or no formatting defined.</p>"

    except Exception as e:
        logging.error(f"Error in process_data: {e}")
        return "<p>An error occurred while processing the data.</p>"

# Simple rule-based intent detection (can be improved)
def detect_intent_and_entities(query):
    if "manager" in query:
        return "manager_query", {}
    elif "salary" in query or "total salary" in query:
        return "salary_query", {}
    elif "employee" in query or "employees" in query:
        return "employee_query", {}
    elif "details" in query or "information" in query:
        return "employee_details_query", {}
    else:
        return None, {}

# Chat route for handling user requests
@app.route('/api/v1/chat', methods=['POST'])
def chat():
    # Try to get the JSON data from the request
    data = request.get_json()
    try:
        # Check if data is None or if query is missing
        if not data or "query" not in data:
            return jsonify({'response': "Please provide a valid 'query' field in the request."}), 400

        query = data["query"]  

        # Detect intent and entities
        intent, entities = detect_intent_and_entities(query)
        if intent is None:
            return jsonify({'response': "I can't understand your request."}), 400

        try:
            sql_query = generate_sql_query(query)
            logging.info(f"Generated SQL: {sql_query}")

            result, columns = execute_query(sql_query)

            formatted_result = process_data(result, intent, columns)  # Intent is not really used for the time being

            return jsonify({'response': formatted_result}), 200

        except Exception as e:  # Catch any unexpected errors
            logging.exception(f"An unexpected error occurred: {e}")  # Log the full traceback
            return jsonify({'response': "An internal server error occurred."}), 500

    except Exception as e:
        # Log and handle JSON parsing errors
        logging.exception(f"Error processing request: {e}")
        return jsonify({'response': "Invalid JSON or missing 'query' field."}), 400

# Main route
@app.route('/')
def index():
    return render_template("index.html")  # Serve an HTML page for the main interface

if __name__ == "__main__":
    app.run(debug=True)
