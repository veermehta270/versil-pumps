# Versil Pumps — Internal R&D Workflow System

A full-stack internal web application built for Versil Pumps to manage 
pump R&D workflows, part approvals, die patterns, and testing cycles.

## Features
- Role-based access control (Boss, Admin, Die Incharge, Other Incharge)
- Pump lifecycle management from creation to final approval
- Die & pattern tracking with date-based progress
- Testing workflow with sequential approval enforcement
- File upload support for engineering drawings
- Multi-user access on shared network

## Tech Stack
- **Backend:** Python, Flask, Flask-Login, Flask-SQLAlchemy
- **Database:** MySQL
- **Auth:** Bcrypt password hashing, session-based login
- **Frontend:** HTML, CSS, Jinja2

## Setup

1. Clone the repo and create a virtual environment:
```bash
   git clone https://github.com/veermehta270/versil-pumps.git
   cd versil-pumps
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
```

2. Set up your MySQL database and create a `.env` file:
```bash
   cp .env.example .env
   # Then edit .env with your actual credentials
```

3. Create the database tables:
```bash
   flask shell
   >>> from extensions import db
   >>> db.create_all()
```

4. Run the app:
```bash
   python app.py
```

## Preview
<img width="1912" height="878" alt="image" src="https://github.com/user-attachments/assets/5b0d459f-c983-4630-9cf7-f6c87ea42d52" />
<img width="1917" height="784" alt="image" src="https://github.com/user-attachments/assets/b0fbdda3-f52e-47b3-9398-840a6a678bf1" />
<img width="1917" height="952" alt="image" src="https://github.com/user-attachments/assets/9a65f16e-87c4-45a9-aa39-8ff87a17aeab" />
<img width="1915" height="799" alt="image" src="https://github.com/user-attachments/assets/0b78ca2d-e2d5-4894-bab7-44a24057ae96" />

