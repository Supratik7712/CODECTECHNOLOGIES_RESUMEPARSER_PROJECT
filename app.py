#Resume parser internship project- Codec technologies
import os
import re
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

import spacy
import pdfplumber
from docx import Document
from flask import Flask, request, jsonify, render_template_string
import pandas as pd


@dataclass
class ContactInfo:
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None

@dataclass
class Education:
    degree: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None
    gpa: Optional[str] = None

@dataclass
class Experience:
    title: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None

@dataclass
class ParsedResume:
    contact_info: ContactInfo
    skills: List[str]
    education: List[Education]
    experience: List[Experience]
    summary: Optional[str] = None
    raw_text: Optional[str] = None

class ResumeParser:
    def __init__(self):
      
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("⚠️  Please install spaCy English model: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        self.skill_keywords = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift'],
            'web': ['html', 'css', 'react', 'vue', 'angular', 'node.js', 'django', 'flask', 'spring'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sqlite'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform'],
            'data': ['pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'tableau', 'powerbi'],
            'tools': ['git', 'jenkins', 'jira', 'confluence', 'slack', 'trello', 'vscode']
        }
        
       
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file using PDFPlumber."""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error extracting PDF: {e}")
        return text

    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from Word document."""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"Error extracting DOCX: {e}")
        return text

    def extract_contact_info(self, text: str) -> ContactInfo:
        """Extract contact information from text."""
        contact = ContactInfo()
        
        email_match = re.search(self.email_pattern, text, re.IGNORECASE)
        if email_match:
            contact.email = email_match.group()
        
        
        phone_match = re.search(self.phone_pattern, text)
        if phone_match:
            contact.phone = phone_match.group()
        
       
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_match:
            contact.linkedin = linkedin_match.group()
        
        if self.nlp:
            doc = self.nlp(text[:1000])
            persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
            if persons:
                contact.name = persons[0]
      
        if not contact.name:
            lines = text.strip().split('\n')
            if lines:
                first_line = lines[0].strip()
                if len(first_line.split()) <= 4 and len(first_line) < 50:
                    contact.name = first_line
        
        return contact

    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text using keyword matching."""
        text_lower = text.lower()
        found_skills = []
        
        for category, skills in self.skill_keywords.items():
            for skill in skills:
                if skill.lower() in text_lower:
                    found_skills.append(skill.title())
        
        return list(dict.fromkeys(found_skills))

    def extract_education(self, text: str) -> List[Education]:
        """Extract education information."""
        education_list = []
        
        patterns = [
            r'(bachelor|master|phd|doctorate|associate|diploma|certificate).*?in\s+([^\n\r]+)',
            r'(b\.?s\.?|m\.?s\.?|ph\.?d\.?|b\.?a\.?|m\.?a\.?)\s+([^\n\r]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                education = Education(
                    degree=match.group(1),
                    institution=match.group(2).strip()
                )
                education_list.append(education)
        
        return education_list

    def extract_experience(self, text: str) -> List[Experience]:
        """Extract work experience."""
        experience_list = []
        
        job_patterns = [
            r'(software engineer|developer|analyst|manager|director|coordinator|specialist)',
            r'(intern|senior|junior|lead|principal|chief)'
        ]
        
        lines = text.split('\n')
        current_exp = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in job_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if current_exp:
                        experience_list.append(current_exp)
                    current_exp = Experience(title=line)
                    break
        
        if current_exp:
            experience_list.append(current_exp)
        
        return experience_list

    def parse_resume(self, file_path: str) -> ParsedResume:
        """Main method to parse a resume file."""
        if file_path.lower().endswith('.pdf'):
            raw_text = self.extract_text_from_pdf(file_path)
        elif file_path.lower().endswith(('.docx', '.doc')):
            raw_text = self.extract_text_from_docx(file_path)
        else:
            raise ValueError("Unsupported file format. Use PDF or DOCX.")
        
        contact_info = self.extract_contact_info(raw_text)
        skills = self.extract_skills(raw_text)
        education = self.extract_education(raw_text)
        experience = self.extract_experience(raw_text)
        
        return ParsedResume(
            contact_info=contact_info,
            skills=skills,
            education=education,
            experience=experience,
            raw_text=raw_text
        )

class SQLiteDatabaseManager:
    def __init__(self, db_path: str = "resumes.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get SQLite database connection."""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize SQLite database tables."""
        with self.get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                linkedin TEXT,
                skills TEXT,
                raw_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS education (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER,
                degree TEXT,
                institution TEXT,
                year TEXT,
                gpa TEXT,
                FOREIGN KEY (resume_id) REFERENCES resumes (id)
            );
            
            CREATE TABLE IF NOT EXISTS experience (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER,
                title TEXT,
                company TEXT,
                duration TEXT,
                description TEXT,
                FOREIGN KEY (resume_id) REFERENCES resumes (id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_resumes_email ON resumes(email);
            CREATE INDEX IF NOT EXISTS idx_resumes_skills ON resumes(skills);
            """)
    
    def store_resume(self, parsed_resume: ParsedResume) -> int:
        """Store parsed resume in SQLite database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            skills_json = json.dumps(parsed_resume.skills)
            
           
            cursor.execute("""
                INSERT INTO resumes (name, email, phone, address, linkedin, skills, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                parsed_resume.contact_info.name,
                parsed_resume.contact_info.email,
                parsed_resume.contact_info.phone,
                parsed_resume.contact_info.address,
                parsed_resume.contact_info.linkedin,
                skills_json,
                parsed_resume.raw_text
            ))
            
            resume_id = cursor.lastrowid
            
         
            for edu in parsed_resume.education:
                cursor.execute("""
                    INSERT INTO education (resume_id, degree, institution, year, gpa)
                    VALUES (?, ?, ?, ?, ?)
                """, (resume_id, edu.degree, edu.institution, edu.year, edu.gpa))
            
          
            for exp in parsed_resume.experience:
                cursor.execute("""
                    INSERT INTO experience (resume_id, title, company, duration, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (resume_id, exp.title, exp.company, exp.duration, exp.description))
            
            conn.commit()
            return resume_id
    
    def search_resumes(self, query: str = None, skills: List[str] = None) -> List[Dict]:
        """Search resumes by text query or skills."""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if skills:
                
                skill_conditions = []
                params = []
                for skill in skills:
                    skill_conditions.append("r.skills LIKE ?")
                    params.append(f'%"{skill.lower()}"%')
                
                sql = f"""
                SELECT r.*, GROUP_CONCAT(e.degree) as degrees, GROUP_CONCAT(ex.title) as job_titles
                FROM resumes r
                LEFT JOIN education e ON r.id = e.resume_id
                LEFT JOIN experience ex ON r.id = ex.resume_id
                WHERE {' OR '.join(skill_conditions)}
                GROUP BY r.id
                ORDER BY r.created_at DESC
                """
                cursor.execute(sql, params)
                
            elif query:
                
                cursor.execute("""
                    SELECT r.*, GROUP_CONCAT(e.degree) as degrees, GROUP_CONCAT(ex.title) as job_titles
                    FROM resumes r
                    LEFT JOIN education e ON r.id = e.resume_id
                    LEFT JOIN experience ex ON r.id = ex.resume_id
                    WHERE r.raw_text LIKE ? OR r.name LIKE ?
                    GROUP BY r.id
                    ORDER BY r.created_at DESC
                """, (f"%{query}%", f"%{query}%"))
                
            else:
              
                cursor.execute("""
                    SELECT r.*, GROUP_CONCAT(e.degree) as degrees, GROUP_CONCAT(ex.title) as job_titles
                    FROM resumes r
                    LEFT JOIN education e ON r.id = e.resume_id
                    LEFT JOIN experience ex ON r.id = ex.resume_id
                    GROUP BY r.id
                    ORDER BY r.created_at DESC
                """)
            
            results = []
            for row in cursor.fetchall():
                result_dict = dict(row)
                
                if result_dict['skills']:
                    try:
                        result_dict['skills'] = json.loads(result_dict['skills'])
                    except:
                        result_dict['skills'] = []
                results.append(result_dict)
            
            return results


app = Flask(__name__)

# Initialize components
parser = ResumeParser()
db_manager = SQLiteDatabaseManager()

@app.route('/')
def index():
    """Main page with upload form and search."""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Parser - VS Code Version</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; padding: 20px; background: #f5f5f5; 
            }
            .container { 
                max-width: 1000px; margin: 0 auto; background: white; 
                padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .header { text-align: center; margin-bottom: 40px; }
            .header h1 { color: #007ACC; margin: 0; }
            .header p { color: #666; margin: 10px 0 0 0; }
            .section { 
                margin: 30px 0; padding: 25px; border: 2px solid #e1e1e1; 
                border-radius: 8px; background: #fafafa;
            }
            .section h2 { color: #333; margin-top: 0; }
            input[type="file"], input[type="text"] { 
                padding: 12px; margin: 8px; border: 2px solid #ddd; 
                border-radius: 5px; font-size: 14px; width: 300px;
            }
            button { 
                padding: 12px 20px; margin: 8px; background: #007ACC; 
                color: white; border: none; border-radius: 5px; 
                cursor: pointer; font-size: 14px; font-weight: bold;
            }
            button:hover { background: #005a9e; }
            .status { 
                padding: 15px; margin: 15px 0; border-radius: 5px; 
                font-weight: bold;
            }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📄 Resume Parser System</h1>
                <p>VS Code Ready • SQLite Database • No PostgreSQL Required</p>
            </div>
            
            <div class="section">
                <h2>📤 Upload Resume</h2>
                <p>Upload a PDF or Word document to extract candidate information.</p>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" name="resume" accept=".pdf,.docx,.doc" required>
                    <button type="submit">Parse Resume</button>
                </form>
            </div>
            
            <div class="section">
                <h2>🔍 Search Resumes</h2>
                <p>Search through all parsed resumes in your database.</p>
                
                <form action="/search" method="get" style="margin-bottom: 15px;">
                    <input type="text" name="q" placeholder="Search by name, skills, or content">
                    <button type="submit">Search All</button>
                </form>
                
                <form action="/search" method="get">
                    <input type="text" name="skills" placeholder="Search by skills (e.g., python,javascript,react)">
                    <button type="submit">Search by Skills</button>
                </form>
            </div>
            
            <div class="section">
                <h2>📊 Quick Actions</h2>
                <a href="/api/stats" style="text-decoration: none;">
                    <button type="button">View Database Stats</button>
                </a>
                <a href="/search" style="text-decoration: none;">
                    <button type="button">View All Resumes</button>
                </a>
            </div>
        </div>
        
        <script>
            // Add some basic client-side functionality
            document.querySelector('form[action="/upload"]').onsubmit = function() {
                const button = this.querySelector('button');
                button.textContent = 'Processing...';
                button.disabled = true;
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route('/upload', methods=['POST'])
def upload_resume():
    """Handle resume upload and parsing."""
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:

        os.makedirs('uploads', exist_ok=True)
        
     
        filename = f"resume_{datetime.now().timestamp()}_{file.filename}"
        file_path = os.path.join('uploads', filename)
        file.save(file_path)
        
        
        parsed_resume = parser.parse_resume(file_path)
        
       
        resume_id = db_manager.store_resume(parsed_resume)
        
        return jsonify({
            'success': True,
            'message': f'Resume parsed successfully! Resume ID: {resume_id}',
            'resume_id': resume_id,
            'extracted_data': {
                'name': parsed_resume.contact_info.name,
                'email': parsed_resume.contact_info.email,
                'skills_count': len(parsed_resume.skills),
                'skills': parsed_resume.skills[:5],  # First 5 skills
                'education_count': len(parsed_resume.education),
                'experience_count': len(parsed_resume.experience)
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/search')
def search_resumes():
    """Search resumes endpoint."""
    query = request.args.get('q')
    skills_param = request.args.get('skills')
    
    skills = None
    if skills_param:
        skills = [s.strip() for s in skills_param.split(',')]
    
    try:
        results = db_manager.search_resumes(query=query, skills=skills)
        return jsonify({
            'success': True,
            'count': len(results),
            'query': query,
            'skills_filter': skills,
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get database statistics."""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM resumes")
            total_resumes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM education")
            total_education = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM experience")
            total_experience = cursor.fetchone()[0]
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_resumes': total_resumes,
                    'total_education_records': total_education,
                    'total_experience_records': total_experience,
                    'database_file': db_manager.db_path
                }
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Resume Parser System Starting...")
    print("📂 Database: SQLite (resumes.db)")
    print("🌐 Web Interface: http://localhost:5000")
    print("💻 Perfect for VS Code development!")
    print("\n" + "="*50)
    
    app.run(debug=True, port=5000, host='0.0.0.0')