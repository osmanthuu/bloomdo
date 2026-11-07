import os
import sqlite3
import json
import uuid
import smtplib
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import pypdf

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'todo.db')

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'cute-pastel-todo-default-key-2026')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL DEFAULT 1,
        title TEXT NOT NULL,
        notes TEXT DEFAULT '',
        due_date TEXT DEFAULT '',
        due_time TEXT DEFAULT '',
        priority TEXT DEFAULT 'medium',
        category TEXT DEFAULT 'Personal',
        list_name TEXT DEFAULT 'Today',
        is_pinned INTEGER DEFAULT 0,
        is_completed INTEGER DEFAULT 0,
        completed_at TEXT DEFAULT '',
        is_archived INTEGER DEFAULT 0,
        recurring TEXT DEFAULT 'none',
        blocked_by_id INTEGER DEFAULT NULL,
        time_estimate_minutes INTEGER DEFAULT 0,
        time_spent_seconds INTEGER DEFAULT 0,
        order_index INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS subtasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        is_completed INTEGER DEFAULT 0,
        order_index INTEGER DEFAULT 0,
        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL DEFAULT 1,
        name TEXT NOT NULL,
        color TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL DEFAULT 1,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '🌸',
        is_locked INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL DEFAULT 1,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '✨',
        target_days INTEGER DEFAULT 7,
        logs_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL DEFAULT 1,
        title TEXT NOT NULL,
        category TEXT DEFAULT 'General',
        target_date TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS countdowns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL DEFAULT 1,
        title TEXT NOT NULL,
        target_date TEXT NOT NULL,
        emoji TEXT DEFAULT '🎉',
        note TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS garden_flowers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL DEFAULT 1,
        task_id INTEGER,
        flower_type TEXT NOT NULL,
        color TEXT NOT NULL,
        bloom_date TEXT NOT NULL,
        x_pct REAL DEFAULT 50.0,
        y_pct REAL DEFAULT 50.0
    );

    CREATE TABLE IF NOT EXISTS stickers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sticker_key TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        emoji TEXT NOT NULL,
        description TEXT NOT NULL,
        unlocked_at TEXT
    );

    CREATE TABLE IF NOT EXISTS mood_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL DEFAULT 1,
        date_str TEXT NOT NULL,
        mood_emoji TEXT NOT NULL,
        note TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS settings (
        user_id INTEGER NOT NULL DEFAULT 1,
        key TEXT NOT NULL,
        value TEXT,
        PRIMARY KEY (user_id, key)
    );

    CREATE TABLE IF NOT EXISTS shared_lists (
        share_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        data_json TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # Seed Default Stickers Catalog (locked by default)
    stk_check = cursor.execute("SELECT COUNT(*) FROM stickers").fetchone()[0]
    if stk_check == 0:
        default_stickers = [
            ('first_bloom', 'First Bloom', '🌸', 'Completed your very first task!', None),
            ('streak_3', 'Sprout Master', '🌱', 'Achieved a 3-day completion streak!', None),
            ('streak_7', 'Flower Queen', '🌺', 'Achieved a 7-day completion streak!', None),
            ('night_owl', 'Moonlit Petal', '🌙', 'Finished a task after 9 PM', None),
            ('early_bird', 'Morning Dew', '☀️', 'Checked off a morning routine task', None),
            ('pomodoro_hero', 'Sweet Strawberry', '🍓', 'Completed 4 Pomodoro focus sessions', None),
            ('garden_lush', 'Botanist Bunny', '🐰', 'Grew 10 flowers in the Garden', None),
            ('tidy_bee', 'Busy Bee', '🐝', 'Cleared all tasks for the day', None)
        ]
        cursor.executemany("INSERT INTO stickers (sticker_key, name, emoji, description, unlocked_at) VALUES (?, ?, ?, ?, ?)", default_stickers)

    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS & AUTH DECORATOR ---
def query_db(query, args=(), one=False):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def get_current_user_id():
    return session.get('user_id')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user_id():
            return jsonify({'error': 'Authentication required. Please log in.', 'authenticated': False}), 401
        return f(*args, **kwargs)
    return decorated_function

def seed_defaults_for_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    # Default Categories
    default_cats = [
        (user_id, 'Personal', '#fbcfe8'),
        (user_id, 'School', '#fef08a'),
        (user_id, 'Home', '#bbf7d0'),
        (user_id, 'Work', '#bfdbfe'),
        (user_id, 'Self-Care', '#e9d5ff')
    ]
    cur.executemany("INSERT INTO categories (user_id, name, color) VALUES (?, ?, ?)", default_cats)

    # Default Lists
    default_lists = [
        (user_id, 'Today', '🌸', 0),
        (user_id, 'This Week', '📅', 0),
        (user_id, 'Someday', '☁️', 0),
        (user_id, 'Secret Diary', '🔒', 1)
    ]
    cur.executemany("INSERT INTO lists (user_id, name, icon, is_locked) VALUES (?, ?, ?, ?)", default_lists)
    conn.commit()
    conn.close()

# --- FRONTEND ROUTING & PWA ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

# --- AUTH & SECURITY API ---
@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    user_count = query_db("SELECT COUNT(*) FROM users", one=True)[0]
    uid = get_current_user_id()
    user = query_db("SELECT id, username FROM users WHERE id = ?", (uid,), one=True) if uid else None

    return jsonify({
        'has_users': user_count > 0,
        'is_authenticated': bool(user),
        'username': user['username'] if user else None,
        'user_id': user['id'] if user else None
    })

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters long.'}), 400

    if not password or len(password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters long.'}), 400

    existing = query_db("SELECT id FROM users WHERE username = ? COLLATE NOCASE", (username,), one=True)
    if existing:
        return jsonify({'error': 'Username is already taken. Please choose another cute name! 🌸'}), 409

    hashed = generate_password_hash(password)
    user_id = execute_db("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))

    # Initialize categories & lists for this new user
    seed_defaults_for_user(user_id)

    # Set Session
    session['user_id'] = user_id
    session['username'] = username

    return jsonify({
        'success': True,
        'username': username,
        'user_id': user_id,
        'message': f'Welcome to Pastel Blooms, {username}! 🌸'
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'Please enter both username and password.'}), 400

    user = query_db("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,), one=True)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'success': False, 'error': 'Invalid username or password.'}), 401

    session['user_id'] = user['id']
    session['username'] = user['username']

    return jsonify({
        'success': True,
        'username': user['username'],
        'user_id': user['id']
    })

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out safely! 🌸'})

# --- TASKS API ---
@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    user_id = get_current_user_id()
    list_name = request.args.get('list')
    category = request.args.get('category')
    search = request.args.get('search')
    filter_status = request.args.get('status', 'all')

    query = "SELECT * FROM tasks WHERE user_id = ?"
    params = [user_id]

    if filter_status == 'archived':
        query += " AND is_archived = 1"
    else:
        query += " AND is_archived = 0"
        if filter_status == 'active':
            query += " AND is_completed = 0"
        elif filter_status == 'completed':
            query += " AND is_completed = 1"

    if list_name and list_name != 'All':
        query += " AND list_name = ?"
        params.append(list_name)

    if category and category != 'All':
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (title LIKE ? OR notes LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term])

    query += " ORDER BY is_pinned DESC, order_index ASC, id DESC"

    tasks = query_db(query, params)
    result = []
    
    conn = get_db()
    cur = conn.cursor()
    for row in tasks:
        t = dict(row)
        subtasks_rows = cur.execute(
            "SELECT * FROM subtasks WHERE task_id = ? ORDER BY order_index ASC, id ASC", (t['id'],)
        ).fetchall()
        t['subtasks'] = [dict(s) for s in subtasks_rows]
        result.append(t)
    conn.close()

    return jsonify(result)

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    user_id = get_current_user_id()
    data = request.json or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    notes = data.get('notes', '')
    due_date = data.get('due_date', '')
    due_time = data.get('due_time', '')
    priority = data.get('priority', 'medium')
    category = data.get('category', 'Personal')
    list_name = data.get('list_name', 'Today')
    is_pinned = 1 if data.get('is_pinned') else 0
    recurring = data.get('recurring', 'none')
    blocked_by_id = data.get('blocked_by_id')
    time_estimate_minutes = int(data.get('time_estimate_minutes', 0) or 0)
    order_index = int(data.get('order_index', 0) or 0)

    task_id = execute_db('''
        INSERT INTO tasks (user_id, title, notes, due_date, due_time, priority, category, list_name, is_pinned,
                           recurring, blocked_by_id, time_estimate_minutes, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, title, notes, due_date, due_time, priority, category, list_name, is_pinned,
          recurring, blocked_by_id, time_estimate_minutes, order_index))

    # Add subtasks if provided
    subtasks = data.get('subtasks', [])
    for idx, s in enumerate(subtasks):
        s_title = s if isinstance(s, str) else s.get('title', '')
        if s_title.strip():
            execute_db('INSERT INTO subtasks (task_id, title, is_completed, order_index) VALUES (?, ?, ?, ?)',
                       (task_id, s_title.strip(), 0, idx))

    created = query_db("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id), one=True)
    res = dict(created)
    res['subtasks'] = [dict(s) for s in query_db("SELECT * FROM subtasks WHERE task_id = ?", (task_id,))]
    return jsonify(res), 201

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_single_task(task_id):
    user_id = get_current_user_id()
    task = query_db("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id), one=True)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    res = dict(task)
    res['subtasks'] = [dict(s) for s in query_db("SELECT * FROM subtasks WHERE task_id = ?", (task_id,))]
    return jsonify(res)

@app.route('/api/tasks/<int:task_id>', methods=['PUT', 'PATCH'])
@login_required
def update_task(task_id):
    user_id = get_current_user_id()
    task = query_db("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id), one=True)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    data = request.json or {}
    title = data.get('title', task['title'])
    notes = data.get('notes', task['notes'])
    due_date = data.get('due_date', task['due_date'])
    due_time = data.get('due_time', task['due_time'])
    priority = data.get('priority', task['priority'])
    category = data.get('category', task['category'])
    list_name = data.get('list_name', task['list_name'])
    is_pinned = data.get('is_pinned', task['is_pinned'])
    recurring = data.get('recurring', task['recurring'])
    blocked_by_id = data.get('blocked_by_id', task['blocked_by_id'])
    time_estimate_minutes = data.get('time_estimate_minutes', task['time_estimate_minutes'])
    time_spent_seconds = data.get('time_spent_seconds', task['time_spent_seconds'])
    is_archived = data.get('is_archived', task['is_archived'])
    order_index = data.get('order_index', task['order_index'])

    # Handle completion status toggle
    is_completed = data.get('is_completed', task['is_completed'])
    completed_at = task['completed_at']
    just_completed = False

    if is_completed != task['is_completed']:
        if is_completed:
            completed_at = datetime.utcnow().isoformat()
            just_completed = True
        else:
            completed_at = ''

    execute_db('''
        UPDATE tasks SET title=?, notes=?, due_date=?, due_time=?, priority=?, category=?, list_name=?,
                         is_pinned=?, is_completed=?, completed_at=?, is_archived=?, recurring=?,
                         blocked_by_id=?, time_estimate_minutes=?, time_spent_seconds=?, order_index=?
        WHERE id=? AND user_id=?
    ''', (title, notes, due_date, due_time, priority, category, list_name, is_pinned,
          is_completed, completed_at, is_archived, recurring, blocked_by_id,
          time_estimate_minutes, time_spent_seconds, order_index, task_id, user_id))

    # If subtasks array provided, replace
    if 'subtasks' in data:
        execute_db("DELETE FROM subtasks WHERE task_id = ?", (task_id,))
        for idx, s in enumerate(data['subtasks']):
            s_title = s.get('title', '').strip() if isinstance(s, dict) else str(s).strip()
            s_done = 1 if (isinstance(s, dict) and s.get('is_completed')) else 0
            if s_title:
                execute_db("INSERT INTO subtasks (task_id, title, is_completed, order_index) VALUES (?, ?, ?, ?)",
                           (task_id, s_title, s_done, idx))

    # If completed and recurring, generate next
    if just_completed and recurring and recurring != 'none':
        try:
            curr_due = datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else date.today()
            if recurring == 'daily':
                next_due = curr_due + timedelta(days=1)
            elif recurring == 'weekly':
                next_due = curr_due + timedelta(days=7)
            elif recurring == 'monthly':
                next_due = curr_due + timedelta(days=30)
            else:
                next_due = curr_due + timedelta(days=1)

            execute_db('''
                INSERT INTO tasks (user_id, title, notes, due_date, due_time, priority, category, list_name, recurring, time_estimate_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, title, notes, next_due.isoformat(), due_time, priority, category, list_name, recurring, time_estimate_minutes))
        except Exception:
            pass

    # If completed, grow flower in user's garden
    flower_info = None
    if just_completed:
        cat_row = query_db("SELECT color FROM categories WHERE name = ? AND user_id = ?", (category, user_id), one=True)
        flower_color = cat_row['color'] if cat_row else '#f472b6'
        
        type_map = {
            'Personal': 'cherry',
            'School': 'daisy',
            'Home': 'sunflower',
            'Work': 'forgetmenot',
            'Self-Care': 'lavender'
        }
        f_type = type_map.get(category, 'cherry')
        import random
        rx = round(random.uniform(10.0, 90.0), 1)
        ry = round(random.uniform(40.0, 85.0), 1)

        fid = execute_db('''
            INSERT INTO garden_flowers (user_id, task_id, flower_type, color, bloom_date, x_pct, y_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, task_id, f_type, flower_color, date.today().isoformat(), rx, ry))
        flower_info = {'id': fid, 'flower_type': f_type, 'color': flower_color, 'x_pct': rx, 'y_pct': ry}

    updated = query_db("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id), one=True)
    res = dict(updated)
    res['subtasks'] = [dict(s) for s in query_db("SELECT * FROM subtasks WHERE task_id = ?", (task_id,))]
    res['new_flower'] = flower_info
    return jsonify(res)

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    user_id = get_current_user_id()
    task = query_db("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id), one=True)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    t_dict = dict(task)
    t_dict['subtasks'] = [dict(s) for s in query_db("SELECT * FROM subtasks WHERE task_id = ?", (task_id,))]

    execute_db("DELETE FROM subtasks WHERE task_id = ?", (task_id,))
    execute_db("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    return jsonify({'success': True, 'deleted_task': t_dict})

@app.route('/api/tasks/reorder', methods=['POST'])
@login_required
def reorder_tasks():
    user_id = get_current_user_id()
    order_list = request.json.get('task_ids', [])
    for idx, tid in enumerate(order_list):
        execute_db("UPDATE tasks SET order_index = ? WHERE id = ? AND user_id = ?", (idx, tid, user_id))
    return jsonify({'success': True})

@app.route('/api/tasks/bulk', methods=['POST'])
@login_required
def bulk_actions():
    user_id = get_current_user_id()
    data = request.json or {}
    task_ids = data.get('task_ids', [])
    action = data.get('action')

    if not task_ids:
        return jsonify({'error': 'No tasks provided'}), 400

    conn = get_db()
    cur = conn.cursor()

    if action == 'delete':
        cur.executemany("DELETE FROM subtasks WHERE task_id = ?", [(t,) for t in task_ids])
        cur.executemany("DELETE FROM tasks WHERE id = ? AND user_id = ?", [(t, user_id) for t in task_ids])
    elif action == 'complete':
        now = datetime.utcnow().isoformat()
        cur.executemany("UPDATE tasks SET is_completed = 1, completed_at = ? WHERE id = ? AND user_id = ?", [(now, t, user_id) for t in task_ids])
    elif action == 'move_list':
        target_list = data.get('list_name', 'Today')
        cur.executemany("UPDATE tasks SET list_name = ? WHERE id = ? AND user_id = ?", [(target_list, t, user_id) for t in task_ids])
    elif action == 'set_tag':
        category = data.get('category', 'Personal')
        cur.executemany("UPDATE tasks SET category = ? WHERE id = ? AND user_id = ?", [(category, t, user_id) for t in task_ids])
    elif action == 'snooze':
        days = int(data.get('days', 1))
        target_date = (date.today() + timedelta(days=days)).isoformat()
        cur.executemany("UPDATE tasks SET due_date = ? WHERE id = ? AND user_id = ?", [(target_date, t, user_id) for t in task_ids])

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'count': len(task_ids)})

@app.route('/api/tasks/<int:task_id>/time', methods=['POST'])
@login_required
def log_task_time(task_id):
    user_id = get_current_user_id()
    data = request.json or {}
    additional_seconds = int(data.get('seconds', 0))
    execute_db("UPDATE tasks SET time_spent_seconds = time_spent_seconds + ? WHERE id = ? AND user_id = ?", (additional_seconds, task_id, user_id))
    task = query_db("SELECT id, time_spent_seconds FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id), one=True)
    return jsonify(dict(task))

# --- SUBTASKS API ---
@app.route('/api/subtasks/<int:subtask_id>/toggle', methods=['POST'])
@login_required
def toggle_subtask(subtask_id):
    subtask = query_db("SELECT * FROM subtasks WHERE id = ?", (subtask_id,), one=True)
    if not subtask:
        return jsonify({'error': 'Subtask not found'}), 404
    new_state = 0 if subtask['is_completed'] else 1
    execute_db("UPDATE subtasks SET is_completed = ? WHERE id = ?", (new_state, subtask_id))
    return jsonify({'id': subtask_id, 'is_completed': new_state})

# --- CATEGORIES & LISTS API ---
@app.route('/api/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    user_id = get_current_user_id()
    if request.method == 'POST':
        name = request.json.get('name', '').strip()
        color = request.json.get('color', '#fbcfe8').strip()
        if not name:
            return jsonify({'error': 'Name required'}), 400
        cid = execute_db("INSERT INTO categories (user_id, name, color) VALUES (?, ?, ?)", (user_id, name, color))
        return jsonify({'id': cid, 'name': name, 'color': color}), 201

    cats = query_db("SELECT * FROM categories WHERE user_id = ? ORDER BY name ASC", (user_id,))
    return jsonify([dict(c) for c in cats])

@app.route('/api/categories/<int:cat_id>', methods=['DELETE'])
@login_required
def delete_category(cat_id):
    user_id = get_current_user_id()
    execute_db("DELETE FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
    return jsonify({'success': True})

@app.route('/api/lists', methods=['GET', 'POST'])
@login_required
def manage_lists():
    user_id = get_current_user_id()
    if request.method == 'POST':
        name = request.json.get('name', '').strip()
        icon = request.json.get('icon', '🌸').strip()
        is_locked = 1 if request.json.get('is_locked') else 0
        if not name:
            return jsonify({'error': 'Name required'}), 400
        lid = execute_db("INSERT INTO lists (user_id, name, icon, is_locked) VALUES (?, ?, ?, ?)", (user_id, name, icon, is_locked))
        return jsonify({'id': lid, 'name': name, 'icon': icon, 'is_locked': is_locked}), 201

    lists = query_db("SELECT * FROM lists WHERE user_id = ? ORDER BY id ASC", (user_id,))
    return jsonify([dict(l) for l in lists])

@app.route('/api/lists/<int:list_id>', methods=['DELETE'])
@login_required
def delete_list(list_id):
    user_id = get_current_user_id()
    execute_db("DELETE FROM lists WHERE id = ? AND user_id = ?", (list_id, user_id))
    return jsonify({'success': True})

# --- HABITS API ---
@app.route('/api/habits', methods=['GET', 'POST'])
@login_required
def manage_habits():
    user_id = get_current_user_id()
    if request.method == 'POST':
        name = request.json.get('name', '').strip()
        icon = request.json.get('icon', '✨').strip()
        target_days = int(request.json.get('target_days', 7))
        if not name:
            return jsonify({'error': 'Name required'}), 400
        hid = execute_db("INSERT INTO habits (user_id, name, icon, target_days, logs_json) VALUES (?, ?, ?, ?, '{}')",
                         (user_id, name, icon, target_days))
        return jsonify({'id': hid, 'name': name, 'icon': icon, 'target_days': target_days, 'logs_json': '{}'}), 201

    habits = query_db("SELECT * FROM habits WHERE user_id = ? ORDER BY id ASC", (user_id,))
    res = []
    for h in habits:
        d = dict(h)
        try:
            d['logs'] = json.loads(d['logs_json'])
        except Exception:
            d['logs'] = {}
        res.append(d)
    return jsonify(res)

@app.route('/api/habits/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    user_id = get_current_user_id()
    habit = query_db("SELECT * FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id), one=True)
    if not habit:
        return jsonify({'error': 'Habit not found'}), 404
    date_str = request.json.get('date', date.today().isoformat())
    logs = json.loads(habit['logs_json'] or '{}')

    current_val = logs.get(date_str, False)
    logs[date_str] = not current_val

    execute_db("UPDATE habits SET logs_json = ? WHERE id = ? AND user_id = ?", (json.dumps(logs), habit_id, user_id))
    return jsonify({'id': habit_id, 'date': date_str, 'completed': logs[date_str], 'logs': logs})

@app.route('/api/habits/<int:habit_id>', methods=['DELETE'])
@login_required
def delete_habit(habit_id):
    user_id = get_current_user_id()
    execute_db("DELETE FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id))
    return jsonify({'success': True})

# --- GOALS API ---
@app.route('/api/goals', methods=['GET', 'POST'])
@login_required
def manage_goals():
    user_id = get_current_user_id()
    if request.method == 'POST':
        title = request.json.get('title', '').strip()
        category = request.json.get('category', 'General')
        target_date = request.json.get('target_date', '')
        notes = request.json.get('notes', '')
        if not title:
            return jsonify({'error': 'Title required'}), 400
        gid = execute_db("INSERT INTO goals (user_id, title, category, target_date, notes) VALUES (?, ?, ?, ?, ?)",
                         (user_id, title, category, target_date, notes))
        return jsonify({'id': gid, 'title': title, 'category': category, 'target_date': target_date, 'notes': notes}), 201

    goals = query_db("SELECT * FROM goals WHERE user_id = ? ORDER BY id DESC", (user_id,))
    return jsonify([dict(g) for g in goals])

@app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
@login_required
def delete_goal(goal_id):
    user_id = get_current_user_id()
    execute_db("DELETE FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
    return jsonify({'success': True})

# --- COUNTDOWNS API ---
@app.route('/api/countdowns', methods=['GET', 'POST'])
@login_required
def manage_countdowns():
    user_id = get_current_user_id()
    if request.method == 'POST':
        title = request.json.get('title', '').strip()
        target_date = request.json.get('target_date', '')
        emoji = request.json.get('emoji', '🎉')
        note = request.json.get('note', '')
        if not title or not target_date:
            return jsonify({'error': 'Title and target date required'}), 400
        cid = execute_db("INSERT INTO countdowns (user_id, title, target_date, emoji, note) VALUES (?, ?, ?, ?, ?)",
                         (user_id, title, target_date, emoji, note))
        return jsonify({'id': cid, 'title': title, 'target_date': target_date, 'emoji': emoji, 'note': note}), 201

    countdowns = query_db("SELECT * FROM countdowns WHERE user_id = ? ORDER BY target_date ASC", (user_id,))
    return jsonify([dict(c) for c in countdowns])

@app.route('/api/countdowns/<int:cd_id>', methods=['DELETE'])
@login_required
def delete_countdown(cd_id):
    user_id = get_current_user_id()
    execute_db("DELETE FROM countdowns WHERE id = ? AND user_id = ?", (cd_id, user_id))
    return jsonify({'success': True})

# --- GARDEN & STICKERS & MOODS ---
@app.route('/api/garden', methods=['GET'])
@login_required
def get_garden():
    user_id = get_current_user_id()
    flowers = query_db("SELECT * FROM garden_flowers WHERE user_id = ? ORDER BY id ASC", (user_id,))
    return jsonify([dict(f) for f in flowers])

@app.route('/api/garden/clear', methods=['POST'])
@login_required
def clear_garden():
    user_id = get_current_user_id()
    execute_db("DELETE FROM garden_flowers WHERE user_id = ?", (user_id,))
    return jsonify({'success': True})

@app.route('/api/stickers', methods=['GET'])
def get_stickers():
    stickers = query_db("SELECT * FROM stickers ORDER BY id ASC")
    return jsonify([dict(s) for s in stickers])

@app.route('/api/stickers/<key>/unlock', methods=['POST'])
def unlock_sticker(key):
    now = datetime.utcnow().isoformat()
    execute_db("UPDATE stickers SET unlocked_at = ? WHERE sticker_key = ? AND unlocked_at IS NULL", (now, key))
    stk = query_db("SELECT * FROM stickers WHERE sticker_key = ?", (key,), one=True)
    return jsonify(dict(stk) if stk else {})

@app.route('/api/moods', methods=['GET', 'POST'])
@login_required
def manage_moods():
    user_id = get_current_user_id()
    if request.method == 'POST':
        date_str = request.json.get('date', date.today().isoformat())
        mood_emoji = request.json.get('mood_emoji', '🌸')
        note = request.json.get('note', '')
        existing = query_db("SELECT id FROM mood_logs WHERE user_id = ? AND date_str = ?", (user_id, date_str), one=True)
        if existing:
            execute_db("UPDATE mood_logs SET mood_emoji = ?, note = ? WHERE id = ?", (mood_emoji, note, existing['id']))
        else:
            execute_db("INSERT INTO mood_logs (user_id, date_str, mood_emoji, note) VALUES (?, ?, ?, ?)", (user_id, date_str, mood_emoji, note))
        return jsonify({'date_str': date_str, 'mood_emoji': mood_emoji, 'note': note})

    moods = query_db("SELECT * FROM mood_logs WHERE user_id = ? ORDER BY date_str DESC LIMIT 30", (user_id,))
    return jsonify([dict(m) for m in moods])

# --- STATS & INSIGHTS ---
@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    user_id = get_current_user_id()
    conn = get_db()
    cur = conn.cursor()

    total_tasks = cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_archived = 0", (user_id,)).fetchone()[0]
    completed_tasks = cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_completed = 1 AND is_archived = 0", (user_id,)).fetchone()[0]
    archived_tasks = cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_archived = 1", (user_id,)).fetchone()[0]
    completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)

    cat_counts = cur.execute('''
        SELECT category, COUNT(*) as count FROM tasks WHERE user_id = ? AND is_archived = 0 GROUP BY category
    ''', (user_id,)).fetchall()
    cat_breakdown = {row['category']: row['count'] for row in cat_counts}

    time_spent_total = cur.execute("SELECT COALESCE(SUM(time_spent_seconds), 0) FROM tasks WHERE user_id = ?", (user_id,)).fetchone()[0]
    time_estimate_total = cur.execute("SELECT COALESCE(SUM(time_estimate_minutes), 0) FROM tasks WHERE user_id = ? AND is_completed = 0", (user_id,)).fetchone()[0]

    today = date.today()
    weekly_activity = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        count = cur.execute('''
            SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed_at LIKE ? AND is_completed = 1
        ''', (user_id, f"{day_str}%")).fetchone()[0]
        weekly_activity.append({
            'date': day_str,
            'day_name': day.strftime('%a'),
            'count': count
        })

    conn.close()

    return jsonify({
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'archived_tasks': archived_tasks,
        'completion_rate': completion_rate,
        'cat_breakdown': cat_breakdown,
        'time_spent_total_seconds': time_spent_total,
        'time_estimate_pending_minutes': time_estimate_total,
        'weekly_activity': weekly_activity
    })

# --- TEMPLATES INJECTION ---
@app.route('/api/templates/<tpl_type>', methods=['POST'])
@login_required
def drop_template(tpl_type):
    user_id = get_current_user_id()
    today_str = date.today().isoformat()
    templates = {
        'morning_routine': [
            ("☕ Sip warm lemon water or green tea", "Hydrate and wake up gently", "high", "Self-Care", 10),
            ("🧘‍♀️ 10-minute morning stretch & breathing", "Awaken muscles with cute gentle stretches", "medium", "Self-Care", 10),
            ("📝 Morning pages / daily 3 intentions", "Write down what will make today sweet", "medium", "Personal", 15),
            ("✨ Quick tidy bedroom & make bed", "A neat room creates a calm mind", "low", "Home", 10)
        ],
        'study_session': [
            ("📚 Organize study materials & clear desk", "Grab cute pens, highlighters, notebook", "medium", "School", 5),
            ("🎯 Review lecture slides & create flashcards", "Focus on key concepts for 25 mins", "high", "School", 30),
            ("🧠 Practice test questions / problem set", "Test active recall without peeking", "high", "School", 45),
            ("🌸 Summarize notes in cute pastel notebook", "Synthesize takeaways into 1 page", "medium", "School", 20)
        ],
        'grocery_run': [
            ("🍓 Fresh berries (strawberries & blueberries)", "Check for sweetest batch", "medium", "Home", 10),
            ("🥛 Oat milk, Greek yogurt & matcha powder", "For delicious breakfast parfaits", "medium", "Home", 10),
            ("🥐 Fresh pastries or sourdough loaf", "Bakery counter", "low", "Home", 10),
            ("💐 Fresh flowers for desk vase", "A cute weekly treat!", "low", "Personal", 5)
        ],
        'self_care_day': [
            ("🛁 Cozy bubble bath with lavender scents", "Dim lights, play lo-fi music", "high", "Self-Care", 30),
            ("💆‍♀️ Sheet mask & skincare routine", "Glowy hydration time", "medium", "Self-Care", 20),
            ("🍵 Brew chamomile tea & read cozy novel", "No screens for 1 relaxing hour", "medium", "Personal", 45),
            ("🕯️ Light scented candle & write gratitude list", "3 sweet moments from this week", "low", "Personal", 15)
        ]
    }

    selected = templates.get(tpl_type, [])
    created = []
    for item in selected:
        tid = execute_db('''
            INSERT INTO tasks (user_id, title, notes, priority, category, due_date, time_estimate_minutes, list_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Today')
        ''', (user_id, item[0], item[1], item[2], item[3], today_str, item[4]))
        created.append(tid)

    return jsonify({'success': True, 'count': len(created)})

# --- SETTINGS API ---
@app.route('/api/settings', methods=['GET', 'POST'])
@login_required
def manage_settings():
    user_id = get_current_user_id()
    if request.method == 'POST':
        data = request.json or {}
        conn = get_db()
        cur = conn.cursor()
        for k, v in data.items():
            cur.execute("INSERT OR REPLACE INTO settings (user_id, key, value) VALUES (?, ?, ?)", (user_id, k, str(v)))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    settings_rows = query_db("SELECT key, value FROM settings WHERE user_id = ?", (user_id,))
    return jsonify({r['key']: r['value'] for r in settings_rows})

# --- DATA EXPORT & IMPORT ---
@app.route('/api/export', methods=['GET'])
@login_required
def export_data():
    user_id = get_current_user_id()
    fmt = request.args.get('format', 'json').lower()
    conn = get_db()
    cur = conn.cursor()

    tasks = [dict(r) for r in cur.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,)).fetchall()]
    for t in tasks:
        t['subtasks'] = [dict(s) for s in cur.execute("SELECT * FROM subtasks WHERE task_id = ?", (t['id'],)).fetchall()]

    habits = [dict(r) for r in cur.execute("SELECT * FROM habits WHERE user_id = ?", (user_id,)).fetchall()]
    goals = [dict(r) for r in cur.execute("SELECT * FROM goals WHERE user_id = ?", (user_id,)).fetchall()]
    categories = [dict(r) for r in cur.execute("SELECT * FROM categories WHERE user_id = ?", (user_id,)).fetchall()]
    lists = [dict(r) for r in cur.execute("SELECT * FROM lists WHERE user_id = ?", (user_id,)).fetchall()]
    conn.close()

    if fmt == 'csv':
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Title', 'Notes', 'Due Date', 'Due Time', 'Priority', 'Category', 'List', 'Completed', 'Recurring', 'Estimate (Mins)', 'Time Spent (Secs)'])
        for t in tasks:
            writer.writerow([
                t['id'], t['title'], t['notes'], t['due_date'], t['due_time'],
                t['priority'], t['category'], t['list_name'],
                'Yes' if t['is_completed'] else 'No',
                t['recurring'], t['time_estimate_minutes'], t['time_spent_seconds']
            ])
        return Response(output.getvalue(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=cute_pastel_tasks.csv'})

    export_payload = {
        'exported_at': datetime.utcnow().isoformat(),
        'tasks': tasks,
        'habits': habits,
        'goals': goals,
        'categories': categories,
        'lists': lists
    }
    return jsonify(export_payload)

@app.route('/api/import', methods=['POST'])
@login_required
def import_data():
    user_id = get_current_user_id()
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    filename = file.filename.lower()

    try:
        content = file.read().decode('utf-8', errors='ignore')
        if filename.endswith('.json'):
            data = json.loads(content)
            tasks = data.get('tasks', [])
            for t in tasks:
                tid = execute_db('''
                    INSERT INTO tasks (user_id, title, notes, due_date, due_time, priority, category, list_name,
                                       is_pinned, is_completed, recurring, time_estimate_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, t.get('title', 'Imported Task'), t.get('notes', ''), t.get('due_date', ''),
                      t.get('due_time', ''), t.get('priority', 'medium'), t.get('category', 'Personal'),
                      t.get('list_name', 'Today'), t.get('is_pinned', 0), t.get('is_completed', 0),
                      t.get('recurring', 'none'), t.get('time_estimate_minutes', 0)))
                for s in t.get('subtasks', []):
                    execute_db('INSERT INTO subtasks (task_id, title, is_completed) VALUES (?, ?, ?)',
                               (tid, s.get('title', ''), s.get('is_completed', 0)))
            return jsonify({'success': True, 'count': len(tasks)})
        else:
            return jsonify({'error': 'Only JSON import is currently supported'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to parse import file: {str(e)}'}), 400

# --- SHARING LISTS ---
@app.route('/api/share', methods=['POST'])
def share_list():
    data = request.json or {}
    title = data.get('title', 'My Pastel To-Do List')
    task_items = data.get('tasks', [])

    share_id = str(uuid.uuid4())[:8]
    payload = json.dumps({'title': title, 'tasks': task_items, 'shared_at': datetime.utcnow().isoformat()})

    execute_db("INSERT INTO shared_lists (share_id, title, data_json) VALUES (?, ?, ?)",
               (share_id, title, payload))

    share_url = f"{request.host_url.rstrip('/')}/share/{share_id}"
    return jsonify({'share_id': share_id, 'share_url': share_url})

@app.route('/share/<share_id>')
def view_shared_list(share_id):
    row = query_db("SELECT * FROM shared_lists WHERE share_id = ?", (share_id,), one=True)
    if not row:
        return render_template('share.html', error="This shared list doesn't exist or has expired! 🌸"), 404
    data = json.loads(row['data_json'])
    return render_template('share.html', title=data.get('title'), tasks=data.get('tasks', []), shared_at=data.get('shared_at'))

# --- AI PDF SUMMARISATION ---
@app.route('/api/ai/summarize-pdf', methods=['POST'])
@login_required
def summarize_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No PDF file uploaded'}), 400

    pdf_file = request.files['file']
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400

    try:
        reader = pypdf.PdfReader(pdf_file)
        text_content = ""
        for idx, page in enumerate(reader.pages):
            if idx > 25:
                break
            extracted = page.extract_text()
            if extracted:
                text_content += extracted + "\n"

        text_content = text_content.strip()
        if not text_content:
            return jsonify({'error': 'No readable text could be extracted from this PDF. It may be a scanned image or protected.'}), 400

        api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()

        if api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                prompt = f"""
                You are a lovely, helpful assistant for a pastel productivity to-do app.
                Please analyze this document text and extract:
                1. A brief 2-3 sentence friendly summary of what the document covers.
                2. A list of actionable tasks or checklist items derived from it.
                
                Document content (first part):
                {text_content[:8000]}
                
                Respond in valid JSON format with this exact schema:
                {{
                    "summary": "friendly summary text...",
                    "tasks": [
                        {{
                            "title": "Actionable task title",
                            "notes": "Context or key detail",
                            "priority": "high" or "medium" or "low",
                            "category": "School" or "Work" or "Personal"
                        }}
                    ]
                }}
                """
                msg = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = msg.content[0].text
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                result = json.loads(response_text)
                return jsonify({
                    'success': True,
                    'summary': result.get('summary', 'PDF processed successfully!'),
                    'tasks': result.get('tasks', []),
                    'ai_powered': True
                })
            except Exception:
                pass

        lines = [line.strip() for line in text_content.split('\n') if len(line.strip()) > 3]
        summary_lines = lines[:3]
        summary = " ".join(summary_lines)
        if len(summary) > 280:
            summary = summary[:280] + "..."

        action_verbs = ['read', 'review', 'complete', 'submit', 'write', 'prepare', 'study', 'email', 'check', 'organize', 'practice', 'finish', 'draft', 'design', 'research']
        generated_tasks = []

        for line in lines:
            lower = line.lower()
            if any(lower.startswith(v) for v in action_verbs) or line.startswith(('•', '-', '*', '1.', '2.', '3.')):
                clean_title = line.lstrip('•-* 0123456789.').strip()
                if 5 <= len(clean_title) <= 120:
                    priority = 'high' if any(w in lower for w in ['urgent', 'important', 'exam', 'due', 'deadline']) else 'medium'
                    category = 'School' if any(w in lower for w in ['chapter', 'study', 'class', 'lecture', 'hw']) else 'Work'
                    generated_tasks.append({
                        'title': clean_title,
                        'notes': 'Extracted from PDF document',
                        'priority': priority,
                        'category': category
                    })
                if len(generated_tasks) >= 8:
                    break

        if not generated_tasks:
            for l in lines[3:9]:
                if len(l) > 10 and len(l) < 90:
                    generated_tasks.append({
                        'title': f"Review: {l}",
                        'notes': 'Extracted section from document',
                        'priority': 'medium',
                        'category': 'Work'
                    })

        return jsonify({
            'success': True,
            'summary': summary or "Extracted important details from your PDF.",
            'tasks': generated_tasks,
            'ai_powered': False,
            'notice': 'PDF extracted with built-in document parser. To unlock Claude 3.5 AI deep summarisation, set ANTHROPIC_API_KEY in your .env file!'
        })

    except Exception as e:
        return jsonify({'error': f'Could not process PDF: {str(e)}'}), 500

# --- OPTIONAL EMAIL SUMMARY ---
@app.route('/api/email/summary', methods=['POST'])
@login_required
def send_email_summary():
    user_id = get_current_user_id()
    recipient = request.json.get('email', '').strip()
    if not recipient:
        return jsonify({'error': 'Recipient email required'}), 400

    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USERNAME')
    smtp_pass = os.getenv('SMTP_PASSWORD')
    smtp_sender = os.getenv('SMTP_SENDER_EMAIL', smtp_user)

    if not smtp_server or not smtp_user or not smtp_pass:
        return jsonify({
            'error': 'SMTP credentials are not configured in .env file. Please configure SMTP_SERVER, SMTP_USERNAME, and SMTP_PASSWORD to send daily email summaries.'
        }), 400

    conn = get_db()
    cur = conn.cursor()
    today_str = date.today().isoformat()
    pending = cur.execute("SELECT title, priority, due_time FROM tasks WHERE user_id = ? AND is_completed = 0 AND due_date = ?", (user_id, today_str)).fetchall()
    completed = cur.execute("SELECT title FROM tasks WHERE user_id = ? AND is_completed = 1 AND completed_at LIKE ?", (user_id, f"{today_str}%")).fetchall()
    conn.close()

    pending_html = ""
    for p in pending:
        time_info = f" at {p['due_time']}" if p['due_time'] else ""
        pending_html += f"<li><b>{p['title']}</b> ({p['priority'].title()}){time_info}</li>"
    if not pending_html:
        pending_html = "<li>All caught up! You are awesome! 🌸</li>"

    completed_html = "".join([f"<li><s>{c['title']}</s></li>" for c in completed])
    if not completed_html:
        completed_html = "<li>No tasks completed yet today</li>"

    html_content = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #fdf2f8; padding: 24px; color: #4b5563;">
        <div style="max-width: 500px; margin: auto; background: white; border-radius: 20px; padding: 28px; box-shadow: 0 4px 15px rgba(244,114,182,0.15); border: 2px solid #fbcfe8;">
          <h2 style="color: #ec4899; text-align: center; margin-top: 0;">🌸 Daily Pastel To-Do Summary</h2>
          <p style="text-align: center; color: #9ca3af; font-size: 14px;">Date: {today_str}</p>
          <hr style="border: none; border-top: 1px dashed #fbcfe8; margin: 18px 0;" />
          
          <h3 style="color: #10b981; font-size: 16px;">✨ Completed Today ({len(completed)})</h3>
          <ul>
            {completed_html}
          </ul>

          <h3 style="color: #f43f5e; font-size: 16px; margin-top: 20px;">🎀 Pending for Today ({len(pending)})</h3>
          <ul>
            {pending_html}
          </ul>

          <p style="text-align: center; font-size: 13px; color: #ec4899; margin-top: 25px;">
            Have a lovely day full of blooms and smiles! 🐰💐
          </p>
        </div>
      </body>
    </html>
    """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🌸 Your Pastel To-Do Summary for {today_str}"
        msg['From'] = smtp_sender
        msg['To'] = recipient
        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_sender, recipient, msg.as_string())
        server.quit()

        return jsonify({'success': True, 'message': f'Summary sent successfully to {recipient}!'})
    except Exception as e:
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🌸 Starting Cute Pastel To-Do App on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
