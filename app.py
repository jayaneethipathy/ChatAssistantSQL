import sqlite3
import spacy
from flask import Flask, request, jsonify, render_template
from datetime import datetime
import logging
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from dateutil.parser import parse, ParserError

# Initialize Flask app
app = Flask(__name__)

# Load the NLP model (spaCy)
nlp = spacy.load("en_core_web_sm")

# Load the Sentence Transformer model - currently not using
sentence_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# SQL Query generation
def generate_sql_query(intent, entities):
    try:
        if intent == "employee_query":
            department = entities.get("department")
            name = entities.get("name")
            conditions = []
            params = []

            if department:
                conditions.append("Department = ?")
                params.append(department)
            if name:
                conditions.append("Name = ?")
                params.append(name)

            if conditions:
                sql_query = "SELECT * FROM Employees WHERE " + " AND ".join(conditions)
            else:
                sql_query = "SELECT * FROM Employees"
            return sql_query, tuple(params)

        elif intent == "manager_query":
            department = entities.get("department")
            if department:
                sql_query = "SELECT Manager FROM Departments WHERE Name = ?"
                params = (department,)
            else:
                return None, None # Handle missing department
        elif intent == "salary_query":
            department = entities.get("department")
            if department:
                sql_query = "SELECT SUM(Salary) FROM Employees WHERE Department = ?"
                params = (department,)
            else:
                return None, None # Handle missing department

        elif intent == "hired_after_query":
            date_str = entities.get("date")
            if date_str:
                try:
                    valid_date = parse(date_str)
                    sql_query = "SELECT * FROM Employees WHERE Hire_Date > ?"
                    params = (valid_date.strftime('%Y-%m-%d'),)
                except ParserError:
                    return None, None  # Return safely if date parsing fails
            else:
                return None, None

        elif intent == "employee_details_query":
            name = entities.get("name")
            if name:
                sql_query = "SELECT * FROM Employees WHERE Name = ?"
                params = (name,)
            else:
                return None, None
        
        elif intent == "employee_count_query":
            department = entities.get("department")
            if department:
                sql_query = "SELECT COUNT(*) FROM Employees WHERE Department = ?"
                params = (department,)
            else:
                sql_query = "SELECT COUNT(*) FROM Employees" # Count all if no department
                params = () # No parameters needed
            return sql_query, params # Return parameters even if empty


        elif intent == "manager_salary_query":
            manager = entities.get("manager")
            if manager:
                sql_query = "SELECT SUM(Salary) FROM Employees WHERE Manager = ?"
                params = (manager,)
            else:
                return None, None

        elif intent == "last_name_query":
            last_name = entities.get("last_name")
            if last_name:
                sql_query = "SELECT * FROM Employees WHERE Last_Name = ?"
                params = (last_name,)
            else:
                return None, None
            
        # (e.g., "employees_by_location")
                
        elif intent == "employees_by_location_query":
            location = entities.get("location")
            if location:
                sql_query = "SELECT * FROM Employees WHERE Location = ?"
                params = (location,)
            else:
                return None, None  
        else:
            return None, None

        return sql_query, tuple(params)

    except Exception as e:
        logging.error(f"Error in generate_sql_query: {e}")
        return None, None

# SQL execution function
def execute_query(query, params=()):
    try:
        with sqlite3.connect('employee_database.db') as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            
            # # Debugging: Print table info
            # cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            # tables = cursor.fetchall()
            # print("Tables in DB:", tables)

            # cursor.execute("PRAGMA table_info(Employees);")
            # employee_columns = cursor.fetchall()
            # print("Employees Table Schema:", employee_columns)
            
            
            return result, columns
        
    except sqlite3.Error as e:
        logging.error(f"SQL Error: {str(e)}")
        return str(e), []

# Data processing using Pandas
def process_data(result, intent,columns):
    if not result:
        logging.error("No data returned from the query.")
        return "<p>No results found.</p>"

    try:
        #columns = [description[0] for description in cursor.description] if cursor.description else []
        df = pd.DataFrame(result, columns=columns)
        logging.info(f"DataFrame created with columns: {columns}")

        if intent == "salary_query":
            if not df.empty:
                df['Salary'] = pd.to_numeric(df['Salary'], errors='coerce')  # Convert Salary to numeric, invalid entries become NaN
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
                return  html_output
            else:
                return "<p>No employee details found for the given criteria.</p>"
        elif intent in ("employee_query", "hired_after_query"):
            if not df.empty:
                return df.to_html(classes='table table-striped',index=False)
            else:
                return "<p>No employees found for the given criteria.</p>"
        elif intent == "manager_query":
            if not df.empty:
                manager = df['Manager'].iloc[0]
                return f"<p>The manager is: {manager}</p>"
            else:
                return "<p>No manager found for the given criteria.</p>"
            
        elif intent == "employee_count_query":
            if not df.empty:
                count = df.iloc[0, 0]
                return f"<p>Total number of employees: {count}</p>"
            else:
                return "<p>No employees found in the given department.</p>"
        elif intent == "manager_salary_query":
            if not df.empty:
                total_salary = df['Salary'].sum()
                return f"<p>Total salary for the manager: {total_salary}</p>"
            else:
                return "<p>No salary data found for the manager.</p>"

        else:
            return "<p>Invalid intent or no formatting defined.</p>"

    except Exception as e:
        logging.error(f"Error in process_data: {e}")
        return "<p>An error occurred while processing the data.</p>"
    
#####**************************************#####
# Simple rule-based intent detection
def detect_intent_and_entities(query):  
    doc = nlp(query.lower())
    intent = None
    entities = {}
    # Handle Greetings and Simple Queries First
    if any(token.text in ["hi", "hai","hello", "hey", "greetings"] for token in doc):
        return "greeting", {}  # New: Greeting intent
# 2. Use spaCy's Entity Recognition More Effectively
    department = None  # Store department entity
    person_name = None # Store person name entity
    date = None  # Store date entity
    last_name = None
    manager_name = None
    
    for ent in doc.ents:
        if ent.label_ == "ORG":
            department = ent.text  # Capture the department
            entities["department"] = department
        elif ent.label_ == "PERSON":
            person_name = ent.text
            entities["name"] = person_name
        elif ent.label_ == "DATE":
            date = ent.text
            entities["date"] = date
        elif ent.label_ == "GPE": #location entity
            location = ent.text
            entities["location"] = location

    # 3. Improved Intent Detection with Context and Dependencies
    if "manager" in doc:
        intent = "manager_query"
        # Check for "of" or "in" to associate with a department
        if department is None:
            for token in doc:
                if token.text in ["of", "in"] and token.head.text == "manager" and department: #token.head is the parent of the token
                    break  # Department is already captured
                elif token.text in ["of", "in"] and token.head.text == "manager" and not department:
                    for child in token.children:
                        if child.dep_ == "pobj" and child.ent_type_ == "ORG": #check if the child is an org and is a prepositional object
                            department = child.text
                            entities["department"] = department
                            break
        if not entities.get("department"): #if no department is found, return none
            return None, None 
    elif "salary" in doc or "total salary" in doc or "salary expense" in doc:
            intent = "salary_query"
    elif "hired" in doc and "after" in doc:
        intent = "hired_after_query"
    elif "employees" in doc or "employee" in doc:
        if "details" in doc or "information" in doc:
            intent = "employee_details_query"
        else:
            intent = "employee_query"
    elif person_name and not intent:
        intent = "employee_details_query"
    elif department and "how many" in doc:
        intent = "employee_count_query"
    elif manager_name and "salary" in doc:
        intent = "manager_salary_query"
    elif last_name and "last name" in doc:
        intent = "last_name_query"

    elif "employees" in doc and "location" in doc:
        intent = "employees_by_location_query"
    return intent, entities
# Chat route for handling user requests
@app.route('/api/v1/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not query:
        return jsonify({'response': "Please enter a valid query."}), 400

    query = data.get("query")

    intent, entities = detect_intent_and_entities(query)  # Use the NLU function
    if intent == "greeting": # Handle the greeting intent
        return jsonify({'response': "Hello! How can I help you?"}), 200
    if intent is None:
        return jsonify({'response': "I can't understand your intent request ."}), 400

    sql_query, params = generate_sql_query(intent, entities)

    if sql_query is None:
        return jsonify({'response': "I can't understand your request-SQL."}), 400

    result, columns,cursur = execute_query(sql_query, params)

    if isinstance(result, str):  # Check for SQL errors
        return jsonify({'response': f"Database Error: {result}"}), 500

    formatted_result = process_data(result, intent,columns)
    return jsonify({'response': formatted_result}), 200

# Main route
@app.route('/')
def index():
    return render_template("index.html")  # Serve an HTML page for the main interface

if __name__ == "__main__":
    app.run(debug=True)
