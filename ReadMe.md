Chat Assistant SQL Query Creator

This project implements a Python-based chat assistant that interacts with a SQLite database to answer employee-related queries. It leverages spaCy for natural language processing, Pandas for data manipulation, and Flask for the web interface.

Features

✅ Accepts natural language queries related to employees, departments, salaries, managers, hire dates, etc.
✅ Converts natural language queries into SQL queries dynamically.
✅ Fetches relevant data from a SQLite database.
✅ Provides clear and formatted responses to user queries.
✅ Handles various query types, including:

1.Listing employees (by department, name, or all)

2.Retrieving manager information (by department)

3.Calculating total salary expense (by department)

4.Listing employees hired after a specific date

5.Fetching employee details (by name)

6.Counting employees (by department or all)

7.Getting total salary for a specific manager

8.Finding employees by last name

9.Searching employees by location

10 Gracefully handles invalid queries, missing data, and database errors.

Getting Started

Prerequisites

Ensure you have the following installed:

Python 3.8 or higher

Docker (recommended for deployment)

Installation & Setup

1. Clone the Repository

git clone https://github.com/jayaneethipathy/ChatAssistantSQL.git
cd ChatAssistantSQL

2. Install Dependencies

pip install -r requirements.txt

3. Download the spaCy Language Model

python -m spacy download en_core_web_sm

4. Create SQLite Database

Ensure that the SQLite database (employee_database.db) is created and populated with relevant employee data.

5. Running the Application (Development Mode)

python app.py

Usage

Once the application is running, you can send natural language queries such as:

"Who is the manager of the Sales department?"

"List all employees in the IT department."

"Show me the employees hired after 2020."

"What is the total salary of employees in the HR department?"

"How many employees are there in Finance?"

The assistant will process the query, generate an SQL statement, execute it on the database, and return the formatted response.

Future Enhancements

🌟 Support for PostgreSQL / MySQL

🌟 Authentication & Role-based Access

🌟 Web-based Chat Interface

🌟 Support for voice-based queries

