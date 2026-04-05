from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import timedelta
from flask_migrate import Migrate
import tempfile
from langgraph_ai.runner import run_quiz_graph, run_roadmap_graph, run_skill_gap_graph

# Initialize Flask app
app = Flask(__name__)


# Configure Secret Key & Sessions
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'e49dad6ce691ff3d216bc6b4e17fdda39936f154eec950149e5c6cd277030782')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.permanent_session_lifetime = timedelta(days=7)
Session(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(BASE_DIR, 'instance')

# Ensure instance folder exists
os.makedirs(instance_path, exist_ok=True)

db_path = os.path.join(instance_path, 'skilltrax.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "connect_args": {
        "timeout": 30,
        "check_same_thread": False   # 🔥 MUST ADD
    }
}

db = SQLAlchemy(app)
migrate = Migrate(app, db)
# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)
    enrolled_courses = db.Column(db.Integer, default=0)
    skills_in_progress = db.Column(db.Integer, default=0)
    completed_paths = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<User {self.email}>'
    
# Quiz Model
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    step_id = db.Column(db.Integer, db.ForeignKey('roadmap_step.id'), nullable=False)
    quiz_data = db.Column(db.JSON, nullable=False)  # Store the quiz JSON data
    score = db.Column(db.Integer, nullable=True)    # Store the user's score (can be null initially)
    total_questions = db.Column(db.Integer, nullable=True)  # Total number of questions
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Relationship with RoadmapStep
    step = db.relationship('RoadmapStep', backref=db.backref('quiz', uselist=False))

# Preparation Model
class Preparation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    job_role = db.Column(db.String(150), nullable=True)

    def __repr__(self):
        return f'<Preparation {self.name}>'

# Roadmap Model
class Roadmap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True) 
    category = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    goals = db.Column(db.String(200), nullable=True)
    custom_requirements = db.Column(db.Text, nullable=True)
    target_completion = db.Column(db.Integer, nullable=True)
    progress = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    preparation_id = db.Column(db.Integer, db.ForeignKey('preparation.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    preparation = db.relationship('Preparation', backref=db.backref('roadmaps', lazy=True))
    user = db.relationship('User', backref=db.backref('roadmaps', lazy=True))
    
# RoadmapStep Model
class RoadmapStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roadmap_id = db.Column(db.Integer, db.ForeignKey('roadmap.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    level = db.Column(db.String(20), nullable=True)
    resource_link_video = db.Column(db.String(255), nullable=True)
    resource_link_webs = db.Column(db.JSON, nullable=True)
    order = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='locked')  # 'locked', 'in_progress', 'completed'
    roadmap = db.relationship('Roadmap', backref=db.backref('steps', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<RoadmapStep {self.title}>'


# Skills Model
class Skills(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('skills', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Skills {self.skill_name}>'


# Project Model
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('projects', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Project {self.project_name}>'


# Experience Model
class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('experiences', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Experience {self.role} at {self.company_name}>'


# Initialize database within app context
with app.app_context():
    db.create_all()

# Close database session properly after each request
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to format file size
def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1048576:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes/1048576:.1f} MB"


def add_completed_roadmap_skill(user_id, roadmap):
    """Add roadmap title as an advanced skill for a user when roadmap is completed."""
    if not roadmap or not roadmap.title:
        return

    skill_name = roadmap.title.strip()
    if not skill_name:
        return

    existing_skill = Skills.query.filter(
        Skills.user_id == user_id,
        db.func.lower(Skills.skill_name) == skill_name.lower()
    ).first()

    if not existing_skill:
        db.session.add(Skills(
            skill_name=skill_name,
            level='advanced',
            user_id=user_id
        ))

# Home Route
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Invalid credentials. Please try again.')
            return render_template('login.html')

        session.permanent = remember
        session['user_id'] = user.id
        session['logged_in'] = True

        return redirect(url_for('dashboard'))

    return render_template('login.html')

# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')

        if not email or not password or not name:
            flash('Please fill all fields')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return render_template('register.html')

        if User.query.filter_by(name=name).first():
            flash('Username already taken. Please choose another.')
            return render_template('register.html')

        new_user = User(
            email=email,
            name=name,
            password=generate_password_hash(password, method='pbkdf2:sha256')
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash("You must log in first!")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("User not found, please log in again.")
        return redirect(url_for('login'))

    # Fetch roadmaps where the user is enrolled (excluding preparation-linked roadmaps)
    enrolled_roadmaps = Roadmap.query.filter_by(
        user_id=user.id,
        preparation_id=None
    ).all()

    # Dynamically calculate user progress stats
    enrolled_courses = len(enrolled_roadmaps)
    skills_in_progress = sum(1 for roadmap in enrolled_roadmaps if 0 < roadmap.progress < 100)
    completed_paths = sum(1 for roadmap in enrolled_roadmaps if roadmap.progress == 100)

    # Update user object with the latest stats
    user.enrolled_courses = enrolled_courses
    user.skills_in_progress = skills_in_progress
    user.completed_paths = completed_paths
    db.session.commit()  # Save changes to the database

    # Check if user has any enrolled roadmaps
    has_roadmaps = enrolled_courses > 0

    preparations = db.session.query(Preparation).join(Roadmap).filter(
        Roadmap.user_id == user.id,
        Roadmap.preparation_id.isnot(None)
    ).distinct().all()
    has_preparations = len(preparations) > 0

    return render_template(
        'dashboard.html',
        user=user,
        roadmaps=enrolled_roadmaps,
        has_roadmaps=has_roadmaps,
        preparations=preparations,
        has_preparations=has_preparations
    )

# Route to handle new roadmap creation
# Replace your existing create_roadmap function with this
@app.route('/create-roadmap', methods=['GET', 'POST'])
def create_roadmap():
    if 'user_id' not in session:
        flash("You must log in first!")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found, please log in again.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get("subject")
        category = request.form.get("subject")
        level = request.form.get("level")
        goals = request.form.getlist("goals")
        custom_requirements = request.form.get("custom_requirements")
        hours_per_week = request.form.get("hours_per_week", type=int)
        target_completion = request.form.get("target_completion", type=int)

        # Validation with flash messages
        if not title:
            flash("Subject is required")
            return render_template("create-roadmap.html", user=user)
        elif not level:
            flash("Please select a knowledge level")
            return render_template("create-roadmap.html", user=user)
        elif not goals:
            flash("Please select at least one learning goal")
            return render_template("create-roadmap.html", user=user)
        
       
        
        # Generate roadmap content
        roadmap_state = run_roadmap_graph(
            subject_area=title,
            knowledge_level=level,
            learning_goals=goals,
            custom_requirement=custom_requirements,
            thread_id=f"roadmap-{user.id}-{title}"
        )
        roadmap_response = roadmap_state.get("roadmap_response")
        if roadmap_state.get("error"):
            flash(roadmap_state.get("error"))
            return render_template("create-roadmap.html", user=user)
        
        # Save roadmap steps to database
        if roadmap_response and 'roadmap' in roadmap_response:
            
            # If validation passes, create the roadmap
            new_roadmap = Roadmap(
                title=roadmap_response['subject'],
                description = roadmap_response['subject_desc'],
                category=roadmap_response['subject'],
                level=level,
                goals=", ".join(goals),
                custom_requirements=custom_requirements,
                target_completion=target_completion,
                progress=0,
                user_id=user.id,
            )

            db.session.add(new_roadmap)
            db.session.commit()

            steps = roadmap_response['roadmap']
            for i, step in enumerate(steps):
                # Set the first step to 'in_progress' and others to 'locked'
                status = 'in_progress' if i == 0 else 'locked'
                
                roadmap_step = RoadmapStep(
                    roadmap_id=new_roadmap.id,
                    title=step['title'],
                    description=step['description'],
                    level=step['level'],
                    resource_link_video=step.get('res_link', ''),
                    resource_link_webs=step.get('resource_link_webs', []),
                    order=i,
                    status=status
                )
                db.session.add(roadmap_step)
            
            db.session.commit()
            
            flash("Roadmap created successfully!")
            return redirect(url_for('view_roadmap', roadmap_id=new_roadmap.id))
        else:
            flash("Failed to generate roadmap. Please try again.")
            return render_template("create-roadmap.html", user=user)

    return render_template("create-roadmap.html", user=user)

# @app.route('/roadmap/<int:roadmap_id>')
# def view_roadmap(roadmap_id):
#     if 'user_id' not in session:
#         flash("You must log in first!")
#         return redirect(url_for('login'))
    
#     user = User.query.get(session['user_id'])
#     if not user:
#         flash("User not found, please log in again.")
#         return redirect(url_for('login'))
    
#     roadmap = Roadmap.query.get_or_404(roadmap_id)
    
#     # Ensure user owns this roadmap
#     if roadmap.user_id != user.id:
#         flash("You don't have permission to view this roadmap.")
#         return redirect(url_for('dashboard'))
    
#     # Check if we're receiving a score from a completed quiz
#     if 'score' in request.args and 'step_id' in request.args:
#         score = int(request.args.get('score'))
#         step_id = int(request.args.get('step_id'))
#         print(f"score: {score}")
        
#         # Find the quiz record for this step
#         quiz = Quiz.query.filter_by(step_id=step_id).first()
        
#         if quiz:
#             # Update the quiz score
#             print("in")
#             quiz.score = score
#             db.session.commit()
#             flash(f"Your quiz score has been recorded: {score}", "success")
#         else:
#             flash("Quiz record not found", "error")
    
#     # Get roadmap steps ordered by their sequence
#     steps = RoadmapStep.query.filter_by(roadmap_id=roadmap_id).order_by(RoadmapStep.order).all()
    
#     # Calculate progress
#     completed_steps = sum(1 for step in steps if step.status == 'completed')
#     if steps:
#         progress_percentage = int((completed_steps / len(steps)) * 100)
#     else:
#         progress_percentage = 0
    
#     # Update roadmap progress
#     roadmap.progress = progress_percentage
#     db.session.commit()
    
#     return render_template(
#         'view-roadmap.html',
#         user=user,
#         roadmap=roadmap,
#         steps=steps,
#         progress=progress_percentage
#     )

@app.route('/roadmap/<int:roadmap_id>')
def view_roadmap(roadmap_id):
    if 'user_id' not in session:
        flash("You must log in first!")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found, please log in again.")
        return redirect(url_for('login'))
    
    roadmap = Roadmap.query.get_or_404(roadmap_id)
    # steps = RoadmapStep.query.filter_by(roadmap_id=roadmap_id).order_by(RoadmapStep.order).all()

    # Ensure user owns this roadmap
    if roadmap.user_id != user.id:
        flash("You don't have permission to view this roadmap.")
        return redirect(url_for('dashboard'))
    
    # Check if we're receiving a score from a completed quiz
    if 'score' in request.args and 'step_id' in request.args:
        score = int(request.args.get('score'))
        step_id = int(request.args.get('step_id'))
        print(f"score: {score}")
        
        # Find the quiz record for this step
        quiz = Quiz.query.filter_by(step_id=step_id).first()
        
        if quiz:
            # Update the quiz score
            print("in")
            quiz.score = score
            db.session.commit()
            flash(f"Your quiz score has been recorded: {score}", "success")
        else:
            flash("Quiz record not found", "error")
    
    # Get roadmap steps ordered by their sequence
    steps = RoadmapStep.query.filter_by(roadmap_id=roadmap_id).order_by(RoadmapStep.order).all()
    step_ids = [step.id for step in steps]
    quizzes = Quiz.query.filter(Quiz.step_id.in_(step_ids)).all()
    quiz_scores = {quiz.step_id: quiz.score for quiz in quizzes}
    # Calculate progress
    completed_steps = sum(1 for step in steps if step.status == 'completed')
    if steps:
        progress_percentage = int((completed_steps / len(steps)) * 100)
    else:
        progress_percentage = 0
    
    # Update roadmap progress
    roadmap.progress = progress_percentage
    if progress_percentage == 100:
        add_completed_roadmap_skill(user.id, roadmap)
    db.session.commit()
    
    return render_template(
        'view-roadmap1.html',
        user=user,
        roadmap=roadmap,
        steps=steps,
        progress=progress_percentage,
        quiz_scores=quiz_scores 
    )

@app.route('/update_step/<int:step_id>', methods=['POST'])
def update_step_status(step_id):
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    step = RoadmapStep.query.get_or_404(step_id)
    roadmap = Roadmap.query.get(step.roadmap_id)
    
    # Verify user owns this roadmap
    if roadmap.user_id != session['user_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['locked', 'in_progress', 'completed']:
        return jsonify({'error': 'Invalid status'}), 400
    
    step.status = new_status
    
    # If a step is completed, unlock the next step
    if new_status == 'completed':
        next_step = RoadmapStep.query.filter_by(
            roadmap_id=step.roadmap_id,
            order=step.order + 1
        ).first()
        
        if next_step and next_step.status == 'locked':
            next_step.status = 'in_progress'
    
    db.session.commit()
    
    # Recalculate roadmap progress
    steps = RoadmapStep.query.filter_by(roadmap_id=step.roadmap_id).all()
    completed_steps = sum(1 for s in steps if s.status == 'completed')
    progress_percentage = int((completed_steps / len(steps)) * 100)
    
    roadmap.progress = progress_percentage
    if progress_percentage == 100:
        add_completed_roadmap_skill(session['user_id'], roadmap)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'progress': progress_percentage
    })

# Update User Statistics
@app.route('/update_stats', methods=['POST'])
def update_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    user.enrolled_courses = data.get('enrolled_courses', user.enrolled_courses)
    user.skills_in_progress = data.get('skills_in_progress', user.skills_in_progress)
    user.completed_paths = data.get('completed_paths', user.completed_paths)

    db.session.commit()
    return jsonify({'message': 'Dashboard stats updated'}), 200

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login'))

# Authentication Provider Placeholder
@app.route('/auth/<provider>')
def auth_provider(provider):
    flash(f'Authentication with {provider} is not implemented yet')
    return redirect(url_for('login'))

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# Show All Users (For Debugging)
@app.route('/show_users')
def show_users():
    users = User.query.all()
    return {"users": [{"id": u.id, "name": u.name, "email": u.email} for u in users]}

# Test endpoint for newly added models
@app.route('/test_models', methods=['GET', 'POST'])
def test_models():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'POST':
        data = request.get_json() or {}

        skill = Skills(
            skill_name=data.get('skill_name', 'Python'),
            level=data.get('skill_level', 'beginner'),
            user_id=user.id
        )
        project = Project(
            project_name=data.get('project_name', 'Sample Project'),
            description=data.get('project_description', 'Test project description'),
            user_id=user.id
        )
        experience = Experience(
            role=data.get('role', 'Intern'),
            company_name=data.get('company_name', 'Example Co'),
            description=data.get('experience_description', 'Test experience description'),
            user_id=user.id
        )

        db.session.add_all([skill, project, experience])
        db.session.commit()

        return jsonify({'message': 'Test records created'}), 201

    skills = Skills.query.filter_by(user_id=user.id).all()
    projects = Project.query.filter_by(user_id=user.id).all()
    experiences = Experience.query.filter_by(user_id=user.id).all()

    return jsonify({
        'skills': [
            {'id': s.id, 'skill_name': s.skill_name, 'level': s.level}
            for s in skills
        ],
        'projects': [
            {'id': p.id, 'project_name': p.project_name, 'description': p.description}
            for p in projects
        ],
        'experiences': [
            {
                'id': e.id,
                'role': e.role,
                'company_name': e.company_name,
                'description': e.description
            }
            for e in experiences
        ]
    })


@app.route('/skill_gap_test', methods=['GET'])
def skill_gap_test():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    job_description_path = request.args.get('path')
    skills = Skills.query.filter_by(user_id=user.id).all()
    skills_payload = [
        {"skill_name": skill.skill_name, "level": skill.level}
        for skill in skills
    ]

    from skill_gap_analysis import test_skill_gap_with_pdf
    result = test_skill_gap_with_pdf(skills_payload, job_description_path)
    return jsonify(result)

# Clear Session Route
@app.route('/clear_session')
def clear_session():
    session.clear()
    flash("Session cleared. Please log in again.")
    return redirect(url_for('login'))
#syllabus route
@app.route('/syllabus')
def syllabus():
    if 'user_id' not in session:
        flash("You must log in first!")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("User not found, please log in again.")
        return redirect(url_for('login'))

    return render_template('syllabus.html', user=user)

# Add new route to handle syllabus upload
@app.route('/upload_syllabus', methods=['POST'])
def upload_syllabus():
    if 'user_id' not in session:
        flash("You must log in first!")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found, please log in again.")
        return redirect(url_for('login'))
    
    # Check if the post request has the file part
    if 'syllabus_pdf' not in request.files:
        flash('No file part in the request')
        return redirect(url_for('syllabus'))
    
    file = request.files['syllabus_pdf']
    
    # If user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('syllabus'))
    
    if file and allowed_file(file.filename):
        # Save the uploaded file temporarily
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        
        try:
            skills = Skills.query.filter_by(user_id=user.id).all()
            skills_payload = [
                {"skill_name": skill.skill_name, "level": skill.level}
                for skill in skills
            ]

            analysis_state = run_skill_gap_graph(
                job_description_path=temp_path,
                skills=skills_payload,
                thread_id=f"skill-gap-{user.id}-{file.filename}"
            )
            if analysis_state.get("error"):
                flash(analysis_state.get("error"))
                return redirect(url_for('syllabus'))

            analysis_result = analysis_state.get('skill_gap_response', {})
            subjects = analysis_result.get('subjects', [])
            job_role = analysis_result.get('job_role', "unknown job role")
            if not subjects:
                flash("No skill gaps identified for this job description.")
                return redirect(url_for('syllabus'))

            prep_name = f"{os.path.splitext(file.filename)[0]}- {job_role}"
            preparation = Preparation(name=prep_name,job_role= job_role)
            db.session.add(preparation)
            db.session.commit()

            for subject in subjects:
                roadmap_state = run_roadmap_graph(
                    subject_area=subject.get('subject area', 'Skill Preparation'),
                    knowledge_level=subject.get('current knowledge level', 'Beginner'),
                    learning_goals=subject.get('learning goals', 'Interview Preparation'),
                    custom_requirement=subject.get('custom requirement', ''),
                    thread_id=f"prep-{user.id}-{preparation.id}-{subject.get('subject area', 'Skill Preparation')}"
                )
                roadmap_response = roadmap_state.get("roadmap_response")

                if roadmap_state.get("error") or not roadmap_response or 'roadmap' not in roadmap_response:
                    continue

                new_roadmap = Roadmap(
                    title=roadmap_response['subject'],
                    description=roadmap_response['subject_desc'],
                    category=roadmap_response['subject'],
                    level=subject.get('current knowledge level', 'Beginner'),
                    goals=subject.get('learning goals', 'Interview Preparation'),
                    custom_requirements=subject.get('custom requirement', ''),
                    target_completion=None,
                    progress=0,
                    preparation_id=preparation.id,
                    user_id=user.id,
                )

                db.session.add(new_roadmap)
                db.session.commit()

                steps = roadmap_response['roadmap']
                for i, step in enumerate(steps):
                    status = 'in_progress' if i == 0 else 'locked'

                    roadmap_step = RoadmapStep(
                        roadmap_id=new_roadmap.id,
                        title=step['title'],
                        description=step['description'],
                        level=step['level'],
                        resource_link_video=step.get('res_link', ''),
                        resource_link_webs=step.get('resource_link_webs', []),
                        order=i,
                        status=status
                    )
                    db.session.add(roadmap_step)

                db.session.commit()

            flash("Preparation roadmaps created successfully!")
            return redirect(url_for('view_preparation', preparation_id=preparation.id))
        except Exception as e:
            # Log the error and flash a message
            print(f"Error processing syllabus: {str(e)}")
            flash('Error processing the syllabus. Please try again.')
            return redirect(url_for('syllabus')) 
        finally:
            # Clean up temporary file
            try:
                os.remove(temp_path)
                os.rmdir(temp_dir)
            except Exception as cleanup_error:
                print(f"Error cleaning up temp file: {cleanup_error}")
    
    flash('Invalid file type. Please upload a PDF, DOCX, or TXT file.')
    return redirect(url_for('syllabus'))


@app.route('/preparation/<int:preparation_id>')
def view_preparation(preparation_id):
    if 'user_id' not in session:
        flash("You must log in first!")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("User not found, please log in again.")
        return redirect(url_for('login'))

    preparation = Preparation.query.get_or_404(preparation_id)
    roadmaps = Roadmap.query.filter_by(
        preparation_id=preparation.id,
        user_id=user.id
    ).all()

    return render_template(
        'preparation-roadmaps.html',
        user=user,
        preparation=preparation,
        roadmaps=roadmaps
    )



@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash("You must log in first!")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash("User not found, please log in again.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        skill_name = request.form.get('skill_name')
        skill_level = request.form.get('skill_level')
        project_name = request.form.get('project_name')
        project_description = request.form.get('project_description')
        role = request.form.get('role')
        company_name = request.form.get('company_name')
        experience_description = request.form.get('experience_description')

        if skill_name and skill_level:
            db.session.add(Skills(
                skill_name=skill_name,
                level=skill_level,
                user_id=user.id
            ))

        if project_name:
            db.session.add(Project(
                project_name=project_name,
                description=project_description,
                user_id=user.id
            ))

        if role and company_name:
            db.session.add(Experience(
                role=role,
                company_name=company_name,
                description=experience_description,
                user_id=user.id
            ))

        db.session.commit()
        flash("Profile details saved.")
        return redirect(url_for('profile'))
    
    # Fetch roadmaps where the user is enrolled
    enrolled_roadmaps = Roadmap.query.filter_by(user_id=user.id).all()

    # Dynamically calculate user progress stats
    enrolled_courses = len(enrolled_roadmaps)
    skills_in_progress = sum(1 for roadmap in enrolled_roadmaps if 0 < roadmap.progress < 100)
    completed_paths = sum(1 for roadmap in enrolled_roadmaps if roadmap.progress == 100)

    # Update user object with the latest stats
    user.enrolled_courses = enrolled_courses
    user.skills_in_progress = skills_in_progress
    user.completed_paths = completed_paths
    db.session.commit()  # Save changes to the database

    # Check if user has any enrolled roadmaps
    has_roadmaps = enrolled_courses > 0

    skills = Skills.query.filter_by(user_id=user.id).all()
    projects = Project.query.filter_by(user_id=user.id).all()
    experiences = Experience.query.filter_by(user_id=user.id).all()

    return render_template(
        'profile.html',
        user=user,
        roadmaps=enrolled_roadmaps,
        has_roadmaps=has_roadmaps,
        skills=skills,
        projects=projects,
        experiences=experiences
    )

@app.route("/quiz/<int:step_id>")
def quiz(step_id):
    # Find the step by ID
    step = RoadmapStep.query.get_or_404(step_id)
    
    # Check if a quiz already exists for this step
    existing_quiz = Quiz.query.filter_by(step_id=step.id).first()
    
    if existing_quiz:
        # Use the existing quiz
        quiz_data = existing_quiz.quiz_data
    else:
        # Generate a new quiz using the step's resource link
        if not step.resource_link_video:
            flash("No video link available for this step.")
            return redirect(url_for("view_roadmap", roadmap_id=step.roadmap_id))

        quiz_state = run_quiz_graph(
            video_url=step.resource_link_video,
            thread_id=f"quiz-{step.id}"
        )
        quiz_data = quiz_state.get("quiz_response")
        if quiz_state.get("error") or not quiz_data:
            print("Unable to generate quiz")
            return redirect(url_for('dashboard'))
        total_que = len(quiz_data["quiz"])
        # Save the new quiz in the database
        new_quiz = Quiz(step_id=step.id, quiz_data=quiz_data,total_questions=total_que)
        db.session.add(new_quiz)
        db.session.commit()
    
    return render_template("quiz.html", quiz=quiz_data, roadmap_id = step.roadmap_id, step_id = step_id)


# Run App
if __name__ == '__main__':
    app.run(debug=True)


