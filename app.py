from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import requests
import random
import os

app = Flask(__name__)
app.secret_key = 'eduboard-secret-key-2025-change-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eduboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ═══════════════════════════════════════════════════════
#  MODELS
# ═══════════════════════════════════════════════════════

class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    first_name    = db.Column(db.String(80),  nullable=False)
    last_name     = db.Column(db.String(80),  nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20),  default='student')   # student | teacher
    grade         = db.Column(db.String(20),  nullable=True)       # student only
    section       = db.Column(db.String(20),  nullable=True)       # student only
    subject       = db.Column(db.String(80),  nullable=True)       # teacher only
    staff_id      = db.Column(db.String(40),  nullable=True)       # teacher only
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}".upper()


class QuizAttempt(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    subject     = db.Column(db.String(100), nullable=False)
    difficulty  = db.Column(db.String(20),  nullable=False)
    score       = db.Column(db.Integer,  default=0)
    total       = db.Column(db.Integer,  default=0)
    percentage  = db.Column(db.Float,   default=0.0)
    time_taken  = db.Column(db.Integer, default=0)   # seconds
    taken_at    = db.Column(db.DateTime, default=datetime.utcnow)
    questions   = db.relationship('QuizQuestion', backref='attempt', lazy=True)


class QuizQuestion(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    attempt_id     = db.Column(db.Integer, db.ForeignKey('quiz_attempt.id'))
    question_text  = db.Column(db.Text,    nullable=False)
    options        = db.Column(db.Text,    nullable=False)
    correct_answer = db.Column(db.String(5), nullable=False)
    user_answer    = db.Column(db.String(5), nullable=True)
    is_correct     = db.Column(db.Boolean,   default=False)


class TeacherQuiz(db.Model):
    """Quiz created by a teacher. Students see it on the quiz page."""
    id          = db.Column(db.Integer, primary_key=True)
    teacher_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name        = db.Column(db.String(120), nullable=False)
    subject     = db.Column(db.String(100), nullable=False)
    difficulty  = db.Column(db.String(20),  default='Medium')
    category    = db.Column(db.String(50),  default='Quiz')
    description = db.Column(db.Text,        nullable=True)
    questions   = db.Column(db.Integer,     default=10)
    duration    = db.Column(db.Integer,     default=30)
    status      = db.Column(db.String(20),  default='active')
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)

    @property
    def teacher(self):
        return User.query.get(self.teacher_id)


# ═══════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════

SUBJECT_MAP = {
    'Mathematics':       {'id': 19, 'emoji': '🔢', 'color': '#7C3AED'},
    'Science':           {'id': 17, 'emoji': '🔬', 'color': '#1DBF73'},
    'History':           {'id': 23, 'emoji': '🏛️',  'color': '#F59E0B'},
    'Geography':         {'id': 22, 'emoji': '🌍', 'color': '#FF5C3A'},
    'Computer Science':  {'id': 18, 'emoji': '💻', 'color': '#06B6D4'},
    'General Knowledge': {'id': 9,  'emoji': '🧠', 'color': '#EC4899'},
    'English':           {'id': 10, 'emoji': '📖', 'color': '#8B5CF6'},
    'Sports':            {'id': 21, 'emoji': '⚽', 'color': '#10B981'},
}

DIFFICULTY_MAP = {'Easy': 'easy', 'Medium': 'medium', 'Hard': 'hard'}


# ═══════════════════════════════════════════════════════
#  AUTH HELPERS
# ═══════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


# ═══════════════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════════════

@app.route('/')
def index():
    if 'user_id' in session:
        u = current_user()
        if u and u.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if 'user_id' in session:
        u = current_user()
        if u and u.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── API: Login ──────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def api_login():
    data  = request.get_json()
    email = data.get('email', '').strip().lower()
    pwd   = data.get('password', '')
    role  = data.get('role', 'student')

    user = User.query.filter_by(email=email, role=role).first()
    if not user or not check_password_hash(user.password_hash, pwd):
        return jsonify({'error': 'Invalid email or password'}), 401

    session['user_id']   = user.id
    session['user_name'] = user.full_name
    session['user_role'] = user.role
    dest = url_for('teacher_dashboard') if user.role == 'teacher' else url_for('dashboard')
    return jsonify({'success': True, 'redirect': dest})


# ── API: Signup ─────────────────────────────────────────
@app.route('/api/signup', methods=['POST'])
def api_signup():
    data  = request.get_json()
    email = data.get('email', '').strip().lower()
    role  = data.get('role', 'student')

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    pwd = data.get('password', '')
    if len(pwd) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    user = User(
        first_name    = data.get('first_name', '').strip(),
        last_name     = data.get('last_name', '').strip(),
        email         = email,
        password_hash = generate_password_hash(pwd),
        role          = role,
        grade         = data.get('grade'),
        section       = data.get('section'),
        subject       = data.get('subject'),
        staff_id      = data.get('staff_id'),
    )
    db.session.add(user)
    db.session.commit()

    session['user_id']   = user.id
    session['user_name'] = user.full_name
    session['user_role'] = user.role
    dest = url_for('teacher_dashboard') if role == 'teacher' else url_for('dashboard')
    return jsonify({'success': True, 'redirect': dest})


# ── API: Google OAuth placeholder ───────────────────────
@app.route('/auth/google')
def auth_google():
    # Plug in Flask-Dance or Authlib here for real Google OAuth
    return jsonify({'error': 'Google OAuth not configured yet'}), 501


# ═══════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════

@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user()
    if user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    stats = _get_user_stats(user)
    return render_template('dashboard.html', user=user, stats=stats)



# ═══════════════════════════════════════════════════════
#  TEACHER DASHBOARD
# ═══════════════════════════════════════════════════════

@app.route('/teacher-dashboard')
@login_required
def teacher_dashboard():
    user = current_user()
    if user.role != 'teacher':
        return redirect(url_for('dashboard'))
    students_raw = User.query.filter_by(role='student').order_by(User.created_at.desc()).all()
    student_data = []
    for s in students_raw:
        attempts = QuizAttempt.query.filter_by(user_id=s.id).all()
        avg  = round(sum(a.percentage for a in attempts) / len(attempts), 1) if attempts else 0
        best = round(max((a.percentage for a in attempts), default=0), 1)
        student_data.append({
            'id': s.id, 'name': s.full_name, 'initials': s.initials,
            'grade': s.grade or '', 'section': s.section or '',
            'quizzes': len(attempts), 'avg': avg, 'best': best,
        })
    all_attempts = QuizAttempt.query.all()
    teacher_stats = {
        'total_students': len(student_data),
        'total_quizzes':  len(all_attempts),
        'avg_score':  round(sum(a.percentage for a in all_attempts) / len(all_attempts), 1) if all_attempts else 0,
        'top_score':  round(max((a.percentage for a in all_attempts), default=0), 1),
    }
    leaderboard = _get_student_leaderboard()
    now = datetime.now().strftime('%A, %B %d, %Y')
    return render_template('teacher_dashboard.html',
                           user=user, students=student_data,
                           teacher_stats=teacher_stats,
                           leaderboard=leaderboard, now=now)


def _get_student_leaderboard(limit=20):
    students = User.query.filter_by(role='student').all()
    rows = []
    for s in students:
        attempts = QuizAttempt.query.filter_by(user_id=s.id).all()
        if not attempts:
            continue
        best_a = max(attempts, key=lambda a: a.percentage)
        avg    = round(sum(a.percentage for a in attempts) / len(attempts), 1)
        rows.append({
            'id': s.id, 'name': s.full_name, 'initials': s.initials,
            'grade': s.grade or '', 'section': s.section or '',
            'quizzes': len(attempts), 'best': round(best_a.percentage, 1),
            'best_subject': best_a.subject, 'avg': avg,
        })
    rows.sort(key=lambda x: x['best'], reverse=True)
    return rows[:limit]


@app.route('/api/student/<int:student_id>')
@login_required
def api_student_detail(student_id):
    user = current_user()
    if user.role != 'teacher':
        return jsonify({'error': 'Forbidden'}), 403
    s = User.query.get_or_404(student_id)
    attempts = QuizAttempt.query.filter_by(user_id=s.id).all()
    avg  = round(sum(a.percentage for a in attempts) / len(attempts), 1) if attempts else 0
    best = round(max((a.percentage for a in attempts), default=0), 1)
    return jsonify({
        'id': s.id, 'name': s.full_name, 'initials': s.initials,
        'grade': s.grade or '', 'section': s.section or '',
        'email': s.email, 'quizzes': len(attempts), 'avg': avg, 'best': best,
    })


@app.route('/api/user-stats')
@login_required
def api_user_stats():
    user = current_user()
    stats = _get_user_stats(user)
    attempts = (QuizAttempt.query.filter_by(user_id=user.id)
                .order_by(QuizAttempt.taken_at.desc()).limit(10).all())
    return jsonify({'stats': stats, 'attempts': [{
        'subject': a.subject, 'difficulty': a.difficulty,
        'score': a.score, 'total': a.total,
        'percentage': a.percentage,
        'taken_at': a.taken_at.strftime('%b %d, %Y'),
    } for a in attempts]})


# ═══════════════════════════════════════════════════════
#  STUDENT RECORDS  (teacher view)
# ═══════════════════════════════════════════════════════

@app.route('/students')
@login_required
def student_records():
    user = current_user()
    if user.role != 'teacher':
        return redirect(url_for('dashboard'))
    students_raw = User.query.filter_by(role='student').order_by(User.created_at.desc()).all()
    student_data = []
    for s in students_raw:
        attempts = QuizAttempt.query.filter_by(user_id=s.id).all()
        avg  = round(sum(a.percentage for a in attempts) / len(attempts), 1) if attempts else 0
        best = round(max((a.percentage for a in attempts), default=0), 1)
        student_data.append({
            'id':      s.id,
            'name':    s.full_name,
            'initials':s.initials,
            'email':   s.email,
            'grade':   s.grade or '—',
            'section': s.section or '—',
            'quizzes': len(attempts),
            'avg':     avg,
            'best':    best,
            'joined':  s.created_at.strftime('%b %d, %Y'),
        })
    now = datetime.now().strftime('%A, %B %d, %Y')
    return render_template('student_records.html', user=user,
                           students=student_data, now=now)


# ─── API: student list ───────────────────────────────────
@app.route('/api/students')
@login_required
def api_students():
    if current_user().role != 'teacher':
        return jsonify({'error': 'Forbidden'}), 403
    students = User.query.filter_by(role='student').all()
    result = []
    for s in students:
        attempts = QuizAttempt.query.filter_by(user_id=s.id).all()
        avg = round(sum(a.percentage for a in attempts) / len(attempts), 1) if attempts else 0
        result.append({
            'id': s.id, 'name': s.full_name, 'initials': s.initials,
            'email': s.email, 'grade': s.grade, 'section': s.section,
            'quizzes': len(attempts), 'avg': avg,
        })
    return jsonify(result)


# ═══════════════════════════════════════════════════════
#  MY SUBJECT
# ═══════════════════════════════════════════════════════

@app.route('/my-subject')
@login_required
def my_subject():
    import json
    user = current_user()
    if user.role != 'teacher':
        return redirect(url_for('dashboard'))
    subject_meta = {
        'Mathematics':{'emoji':'🔢','color':'#7C3AED'},
        'Science':{'emoji':'🔬','color':'#059669'},
        'History':{'emoji':'🏛️','color':'#D97706'},
        'Geography':{'emoji':'🌍','color':'#DC2626'},
        'Computer Science':{'emoji':'💻','color':'#0EA5E9'},
        'General Knowledge':{'emoji':'🧠','color':'#EC4899'},
        'English':{'emoji':'📖','color':'#8B5CF6'},
        'Sports':{'emoji':'⚽','color':'#10B981'},
    }
    all_attempts = QuizAttempt.query.order_by(QuizAttempt.taken_at.asc()).all()
    subj_map = {}
    for a in all_attempts:
        if not a.user_id:
            continue
        subj_map.setdefault(a.subject, {}).setdefault(a.user_id, []).append(a)
    subjects_list, subjects_js = [], {}
    for subj_name in sorted(subj_map.keys()):
        meta  = subject_meta.get(subj_name, {'emoji':'📚','color':'#7C3AED'})
        student_rows = []
        for uid, atts in subj_map[subj_name].items():
            u = User.query.get(uid)
            if not u:
                continue
            scores    = [a.percentage for a in atts]
            avg_score = round(sum(scores)/len(scores), 1)
            last_score = round(atts[-1].percentage, 1)
            trend = [round(a.percentage, 1) for a in atts[-6:]]
            if avg_score >= 90:   status = 'excellent'
            elif avg_score >= 80: status = 'good'
            elif avg_score >= 65: status = 'average'
            else:                 status = 'at-risk'
            badges = []
            if avg_score >= 90: badges.append('🏆 Topper')
            if len(scores) >= 5 and min(scores) >= 70: badges.append('⭐ Consistent')
            if len(scores) >= 3 and scores[-1] > scores[0]: badges.append('📈 Improving')
            if status == 'at-risk': badges.append('⚠ Needs Help')
            diff_scores = {}
            for a in atts:
                diff_scores.setdefault(a.difficulty, []).append(a.percentage)
            difficulty_breakdown = [
                {'difficulty': d, 'avg': round(sum(v)/len(v), 1)}
                for d, v in sorted(diff_scores.items())
            ]
            quiz_history = [{
                'subject': a.subject, 'difficulty': a.difficulty,
                'score': round(a.percentage, 1),
                'taken_at': a.taken_at.strftime('%b %d, %Y'),
            } for a in reversed(atts)]
            student_rows.append({
                'id': f"S{u.id:03d}", 'uid': u.id, 'name': u.full_name,
                'score': avg_score, 'lastQuiz': last_score,
                'quizzes': len(atts), 'att': 95, 'trend': trend,
                'status': status, 'badges': badges,
                'best': subj_name, 'weak': '—',
                'difficulty_breakdown': difficulty_breakdown,
                'quiz_history': quiz_history,
            })
        student_rows.sort(key=lambda x: x['score'], reverse=True)
        for i, s in enumerate(student_rows):
            s['rank'] = i + 1
        subjects_list.append({'name': subj_name, 'student_count': len(student_rows),
                               'color': meta['color'], 'emoji': meta['emoji']})
        subjects_js[subj_name] = {
            'color': meta['color'], 'icon': meta['emoji'], 'count': len(student_rows),
            'topics': [subj_name], 'quizTopics': [subj_name], 'students': student_rows,
        }
    return render_template('my_subject.html', user=user,
                           subjects=subjects_list,
                           subjects_json=json.dumps(subjects_js),
                           now=datetime.now().strftime('%A, %B %d, %Y'))


# ═══════════════════════════════════════════════════════
#  CREATE QUIZ
# ═══════════════════════════════════════════════════════

@app.route('/create-quiz')
@login_required
def create_quiz():
    import json
    user = current_user()
    if user.role != 'teacher':
        return redirect(url_for('dashboard'))

    # Load teacher-created quizzes from DB
    teacher_quizzes = (TeacherQuiz.query
                       .filter_by(teacher_id=user.id)
                       .order_by(TeacherQuiz.created_at.desc()).all())

    quizzes_list = []
    for tq in teacher_quizzes:
        # Count how many students attempted this quiz (matched by subject+difficulty)
        attempts = QuizAttempt.query.filter_by(
            subject=tq.subject, difficulty=tq.difficulty
        ).all()
        student_count = len(set(a.user_id for a in attempts if a.user_id))
        avg_score = round(sum(a.percentage for a in attempts) / len(attempts), 1) if attempts else 0

        quizzes_list.append({
            'id':          tq.id,
            'name':        tq.name,
            'subject':     tq.subject,
            'difficulty':  tq.difficulty,
            'category':    tq.category,
            'description': tq.description or '',
            'questions':   tq.questions,
            'duration':    tq.duration,
            'status':      'Active' if tq.status == 'active' else 'Draft',
            'students':    student_count,
            'avg_score':   avg_score,
            'createdDate': tq.created_at.strftime('%b %d, %Y'),
        })

    quiz_stats = {
        'active':         len([q for q in quizzes_list if q['status'] == 'Active']),
        'total_students': db.session.query(QuizAttempt.user_id).distinct().count(),
        'total_attempts': sum(q['students'] for q in quizzes_list),
    }
    return render_template('quiz_management.html', user=user,
                           quizzes_json=json.dumps(quizzes_list),
                           quiz_stats=quiz_stats,
                           now=datetime.now().strftime('%A, %B %d, %Y'))


# ── Teacher Quiz CRUD API ────────────────────────────────

@app.route('/api/teacher-quiz', methods=['POST'])
@login_required
def api_save_teacher_quiz():
    user = current_user()
    if user.role != 'teacher':
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    if not data.get('name') or not data.get('subject') or not data.get('category'):
        return jsonify({'error': 'Name, subject and category are required'}), 400
    tq = TeacherQuiz(
        teacher_id  = user.id,
        name        = data['name'].strip(),
        subject     = data['subject'],
        difficulty  = data.get('difficulty', 'Medium'),
        category    = data.get('category', 'Quiz'),
        description = data.get('description', ''),
        questions   = int(data.get('questions', 10)),
        duration    = int(data.get('duration', 30)),
        status      = data.get('status', 'active'),
    )
    db.session.add(tq)
    db.session.commit()
    return jsonify({'success': True, 'id': tq.id,
                    'message': f'Quiz "{tq.name}" saved and visible to students!'})


@app.route('/api/teacher-quiz/<int:quiz_id>', methods=['DELETE'])
@login_required
def api_delete_teacher_quiz(quiz_id):
    user = current_user()
    if user.role != 'teacher':
        return jsonify({'error': 'Forbidden'}), 403
    tq = TeacherQuiz.query.get_or_404(quiz_id)
    if tq.teacher_id != user.id:
        return jsonify({'error': 'Not your quiz'}), 403
    db.session.delete(tq)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/teacher-quizzes')
@login_required
def api_teacher_quizzes():
    tqs = TeacherQuiz.query.filter_by(status='active').order_by(TeacherQuiz.created_at.desc()).all()
    return jsonify([{
        'id': tq.id, 'name': tq.name, 'subject': tq.subject,
        'difficulty': tq.difficulty, 'category': tq.category,
        'description': tq.description or '',
        'questions': tq.questions, 'duration': tq.duration,
        'teacher': tq.teacher.full_name if tq.teacher else 'Teacher',
    } for tq in tqs])


# ═══════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════

@app.route('/analytics')
@login_required
def analytics():
    user  = current_user()
    stats = _get_user_stats(user)
    subject_stats = _get_subject_stats(user)
    return render_template('analytics.html', user=user, stats=stats, subject_stats=subject_stats)


# ── API: Analytics data (JSON for chart updates) ────────
@app.route('/api/analytics')
@login_required
def api_analytics():
    user = current_user()
    return jsonify({
        'stats':         _get_user_stats(user),
        'subject_stats': _get_subject_stats(user),
        'leaderboard':   _get_leaderboard(),
    })


def _get_user_stats(user):
    if not user:
        return {}
    attempts = QuizAttempt.query.filter_by(user_id=user.id).all()
    total_quizzes = len(attempts)
    avg_score = round(sum(a.percentage for a in attempts) / total_quizzes, 1) if attempts else 0
    best_score = max((a.percentage for a in attempts), default=0)
    total_time = sum(a.time_taken for a in attempts)
    return {
        'total_quizzes': total_quizzes,
        'avg_score':     avg_score,
        'best_score':    round(best_score, 1),
        'total_time_min': round(total_time / 60, 1),
    }


def _get_subject_stats(user):
    if not user:
        return []
    rows = {}
    for a in QuizAttempt.query.filter_by(user_id=user.id).all():
        if a.subject not in rows:
            rows[a.subject] = {'scores': [], 'count': 0}
        rows[a.subject]['scores'].append(a.percentage)
        rows[a.subject]['count'] += 1
    result = []
    for subj, data in rows.items():
        avg = round(sum(data['scores']) / len(data['scores']), 1)
        info = SUBJECT_MAP.get(subj, {'emoji': '📚', 'color': '#7C3AED'})
        result.append({'subject': subj, 'avg': avg, 'count': data['count'],
                       'emoji': info['emoji'], 'color': info['color']})
    return sorted(result, key=lambda x: x['avg'], reverse=True)


def _get_leaderboard(limit=10):
    rows = (db.session.query(QuizAttempt, User)
            .join(User, QuizAttempt.user_id == User.id, isouter=True)
            .order_by(QuizAttempt.percentage.desc())
            .limit(limit).all())
    result = []
    for attempt, user in rows:
        name = user.full_name if user else 'Anonymous'
        initials = user.initials if user else '??'
        result.append({
            'name':       name,
            'initials':   initials,
            'subject':    attempt.subject,
            'difficulty': attempt.difficulty,
            'score':      attempt.score,
            'total':      attempt.total,
            'percentage': attempt.percentage,
            'taken_at':   attempt.taken_at.strftime('%b %d, %Y'),
        })
    return result


# ═══════════════════════════════════════════════════════
#  QUIZ ROUTES
# ═══════════════════════════════════════════════════════

@app.route('/quiz')
@login_required
def quiz_select():
    user = current_user()
    teacher_quizzes = (TeacherQuiz.query
                       .filter_by(status='active')
                       .order_by(TeacherQuiz.created_at.desc()).all())
    tq_list = [{
        'id': tq.id, 'name': tq.name, 'subject': tq.subject,
        'difficulty': tq.difficulty, 'category': tq.category,
        'description': tq.description or '',
        'questions': tq.questions, 'duration': tq.duration,
        'teacher': tq.teacher.full_name if tq.teacher else 'Teacher',
        'created_at': tq.created_at.strftime('%b %d, %Y'),
    } for tq in teacher_quizzes]
    return render_template('quiz_select.html', user=user,
                           subjects=SUBJECT_MAP, teacher_quizzes=tq_list)

@app.route('/quiz/take')
@login_required
def quiz_take():
    user         = current_user()
    subject      = request.args.get('subject', 'General Knowledge')
    difficulty   = request.args.get('difficulty', 'Medium')
    num_questions = int(request.args.get('num_questions', 10))
    return render_template('quiz_take.html',
                           user=user,
                           subject=subject,
                           difficulty=difficulty,
                           num_questions=num_questions,
                           subject_info=SUBJECT_MAP.get(subject, SUBJECT_MAP['General Knowledge']))

@app.route('/api/fetch-quiz')
@login_required
def api_fetch_quiz():
    subject   = request.args.get('subject', 'General Knowledge')
    difficulty = request.args.get('difficulty', 'Medium')
    amount    = int(request.args.get('amount', 10))
    cat_id    = SUBJECT_MAP.get(subject, {}).get('id', 9)
    diff      = DIFFICULTY_MAP.get(difficulty, 'medium')

    url = (f"https://opentdb.com/api.php"
           f"?amount={amount}&category={cat_id}&difficulty={diff}&type=multiple")
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get('response_code') != 0:
            return jsonify({'error': 'Could not fetch questions', 'code': data.get('response_code')}), 400
        questions = []
        for q in data['results']:
            options = q['incorrect_answers'] + [q['correct_answer']]
            random.shuffle(options)
            correct_idx = options.index(q['correct_answer'])
            questions.append({'question': q['question'], 'options': options,
                              'correct': correct_idx, 'category': q['category']})
        return jsonify({'questions': questions, 'subject': subject, 'difficulty': difficulty})
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-quiz', methods=['POST'])
@login_required
def api_submit_quiz():
    data       = request.get_json()
    subject    = data.get('subject', 'General Knowledge')
    difficulty = data.get('difficulty', 'Medium')
    answers    = data.get('answers', [])
    time_taken = data.get('time_taken', 0)

    score = sum(1 for a in answers if a.get('user_answer') == a.get('correct'))
    total = len(answers)
    pct   = round((score / total * 100) if total else 0, 1)

    attempt = QuizAttempt(
        user_id=session.get('user_id'),
        subject=subject, difficulty=difficulty,
        score=score, total=total, percentage=pct, time_taken=time_taken,
    )
    db.session.add(attempt)
    db.session.flush()

    for a in answers:
        db.session.add(QuizQuestion(
            attempt_id=attempt.id,
            question_text=a.get('question', ''),
            options=str(a.get('options', [])),
            correct_answer=str(a.get('correct', '')),
            user_answer=str(a.get('user_answer', '')),
            is_correct=(a.get('user_answer') == a.get('correct')),
        ))
    db.session.commit()
    return jsonify({'score': score, 'total': total, 'percentage': pct,
                    'attempt_id': attempt.id, 'time_taken': time_taken})

@app.route('/api/leaderboard')
def api_leaderboard():
    return jsonify(_get_leaderboard())

# ── API: current user info for JS ───────────────────────
@app.route('/api/me')
@login_required
def api_me():
    u = current_user()
    return jsonify({'name': u.full_name, 'initials': u.initials, 'role': u.role, 'email': u.email})


# ═══════════════════════════════════════════════════════
#  LEADERBOARD
# ═══════════════════════════════════════════════════════

@app.route('/leaderboard')
@login_required
def leaderboard():
    user = current_user()
    board = _get_leaderboard(50)
    stats = _get_leaderboard_stats()
    return render_template('leaderboard.html', user=user, board=board, stats=stats)


def _get_leaderboard_stats():
    attempts = QuizAttempt.query.all()
    if not attempts:
        return {'highest': 0, 'participants': 0, 'avg': 0}
    return {
        'highest': round(max(a.percentage for a in attempts), 1),
        'participants': db.session.query(QuizAttempt.user_id).distinct().count(),
        'avg': round(sum(a.percentage for a in attempts) / len(attempts), 1),
    }


# ═══════════════════════════════════════════════════════
#  MARKS ANALYZER
# ═══════════════════════════════════════════════════════

@app.route('/marks-analyzer')
@login_required
def marks_analyzer():
    user = current_user()
    return render_template('marks_analyzer.html', user=user)


# (student_records and api_students moved to teacher section above)





# ═══════════════════════════════════════════════════════
#  HEALTH & WELLNESS
# ═══════════════════════════════════════════════════════

@app.route('/health')
@login_required
def health():
    user = current_user()
    return render_template('health.html', user=user)




# ═══════════════════════════════════════════════════════
#  INIT DB
# ═══════════════════════════════════════════════════════
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)