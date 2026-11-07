import os
import sqlite3
import json
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
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
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        name TEXT UNIQUE NOT NULL,
        color TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icon TEXT DEFAULT '🌸',
        is_locked INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '✨',
        target_days INTEGER DEFAULT 7,
        logs_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT DEFAULT 'General',
        target_date TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS countdowns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        target_date TEXT NOT NULL,
        emoji TEXT DEFAULT '🎉',
        note TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS garden_flowers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        date_str TEXT UNIQUE NOT NULL,
        mood_emoji TEXT NOT NULL,
        note TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS shared_lists (
        share_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        data_json TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # Seed Default Categories if empty
    cat_check = cursor.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if cat_check == 0:
        default_cats = [
            ('Personal', '#fbcfe8'),
            ('School', '#fef08a'),
            ('Home', '#bbf7d0'),
            ('Work', '#bfdbfe'),
            ('Self-Care', '#e9d5ff')
        ]
        cursor.executemany("INSERT INTO categories (name, color) VALUES (?, ?)", default_cats)

    # Seed Default Lists if empty
    list_check = cursor.execute("SELECT COUNT(*) FROM lists").fetchone()[0]
    if list_check == 0:
        default_lists = [
            ('Today', '🌸', 0),
            ('This Week', '📅', 0),
            ('Someday', '☁️', 0),
            ('Secret Diary', '🔒', 1)
        ]
        cursor.executemany("INSERT INTO lists (name, icon, is_locked) VALUES (?, ?, ?)", default_lists)

    # Seed Stickers if empty
    stk_check = cursor.execute("SELECT COUNT(*) FROM stickers").fetchone()[0]
    if stk_check == 0:
        default_stickers = [
            ('first_bloom', 'First Bloom', '🌸', 'Completed your very first task!', datetime.utcnow().isoformat()),
            ('streak_3', 'Sprout Master', '🌱', 'Achieved a 3-day completion streak!', None),
            ('streak_7', 'Flower Queen', '🌺', 'Achieved a 7-day completion streak!', None),
            ('night_owl', 'Moonlit Petal', '🌙', 'Finished a task after 9 PM', None),
            ('early_bird', 'Morning Dew', '☀️', 'Checked off a morning routine task', None),
            ('pomodoro_hero', 'Sweet Strawberry', '🍓', 'Completed 4 Pomodoro focus sessions', None),
            ('garden_lush', 'Botanist Bunny', '🐰', 'Grew 10 flowers in the Garden', None),
            ('tidy_bee', 'Busy Bee', '🐝', 'Cleared all tasks for the day', None)
        ]
        cursor.executemany("INSERT INTO stickers (sticker_key, name, emoji, description, unlocked_at) VALUES (?, ?, ?, ?, ?)", default_stickers)

    # Seed Tasks if empty
    task_check = cursor.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if task_check == 0:
        today_str = date.today().isoformat()
        tomorrow_str = (date.today() + timedelta(days=1)).isoformat()

        cursor.execute('''
            INSERT INTO tasks (title, notes, due_date, due_time, priority, category, list_name, is_pinned, is_completed, time_estimate_minutes, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("🌸 Welcome to your Cute Pastel To-Do list!", "Explore themes, flower cursors, drag & drop widgets, and watch your cute mascot cheer!", today_str, "12:00", "high", "Personal", "Today", 1, 0, 15, 0))
        t1_id = cursor.lastrowid

        cursor.executemany("INSERT INTO subtasks (task_id, title, is_completed, order_index) VALUES (?, ?, ?, ?)", [
            (t1_id, "Check off this subtask to hear the sweet chime 🎵", 0, 0),
            (t1_id, "Switch to lavender or dark pastel theme in top menu 💜", 0, 1),
            (t1_id, "Hover over buttons to watch the flower cursor bloom 🌼", 0, 2),
            (t1_id, "Plant your first flower in the Garden tab 🌱", 0, 3)
        ])

        cursor.execute('''
            INSERT INTO tasks (title, notes, due_date, due_time, priority, category, list_name, is_pinned, is_completed, time_estimate_minutes, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("🍵 Make strawberry matcha & do morning journaling", "Add warm milk foam and 2 spoons of honey ✨", today_str, "09:30", "high", "Self-Care", "Today", 0, 0, 20, 1))

        cursor.execute('''
            INSERT INTO tasks (title, notes, due_date, due_time, priority, category, list_name, is_pinned, is_completed, time_estimate_minutes, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("📚 Study session: Review summary notes & flashcards", "Use the Pomodoro timer in the widget or focus mode!", today_str, "16:00", "medium", "School", "Today", 0, 0, 45, 2))

        cursor.execute('''
            INSERT INTO tasks (title, notes, due_date, due_time, priority, category, list_name, is_pinned, is_completed, time_estimate_minutes, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("🛒 Grocery run: strawberries, bakery buns & fresh lavender", "Check bakery corner for fresh croissants", tomorrow_str, "18:00", "low", "Home", "This Week", 0, 0, 30, 3))

    # Seed Habits if empty
    habit_check = cursor.execute("SELECT COUNT(*) FROM habits").fetchone()[0]
    if habit_check == 0:
        today_str = date.today().isoformat()
        sample_logs = json.dumps({today_str: True})
        default_habits = [
            ("Drink 8 glasses of water", "💧", 7, sample_logs),
            ("Read 15 minutes of a cute book", "📖", 7, sample_logs),
            ("10-minute mindful stretch", "🧘‍♀️", 7, "{}"),
            ("Water the cozy house plants", "🪴", 7, sample_logs)
        ]
        cursor.executemany("INSERT INTO habits (name, icon, target_days, logs_json) VALUES (?, ?, ?, ?)", default_habits)

    # Seed Goals if empty
    goal_check = cursor.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
    if goal_check == 0:
        cursor.execute("INSERT INTO goals (title, category, target_date, notes) VALUES (?, ?, ?, ?)",
                       ("🌸 Complete Semester with Straight A's", "School", (date.today() + timedelta(days=60)).isoformat(), "Daily focus study sessions"))
        cursor.execute("INSERT INTO goals (title, category, target_date, notes) VALUES (?, ?, ?, ?)",
                       ("✨ Read 12 cozy novels this year", "Self-Care", (date.today() + timedelta(days=120)).isoformat(), "Track reading time & notes"))

    # Seed Countdowns if empty
    cd_check = cursor.execute("SELECT COUNT(*) FROM countdowns").fetchone()[0]
    if cd_check == 0:
        cursor.execute("INSERT INTO countdowns (title, target_date, emoji, note) VALUES (?, ?, ?, ?)",
                       ("🎂 Birthday Celebration", (date.today() + timedelta(days=25)).isoformat(), "🎂", "Bake strawberry shortcake!"))
        cursor.execute("INSERT INTO countdowns (title, target_date, emoji, note) VALUES (?, ?, ?, ?)",
                       ("✈️ Weekend Cabin Getaway", (date.today() + timedelta(days=14)).isoformat(), "🌸", "Cozy cabin by the pine lake"))

    # Seed Initial Flowers in Garden
    flower_check = cursor.execute("SELECT COUNT(*) FROM garden_flowers").fetchone()[0]
    if flower_check == 0:
        cursor.execute("INSERT INTO garden_flowers (task_id, flower_type, color, bloom_date, x_pct, y_pct) VALUES (?, ?, ?, ?, ?, ?)",
                       (None, "cherry", "#f472b6", date.today().isoformat(), 30.0, 65.0))
        cursor.execute("INSERT INTO garden_flowers (task_id, flower_type, color, bloom_date, x_pct, y_pct) VALUES (?, ?, ?, ?, ?, ?)",
                       (None, "daisy", "#facc15", date.today().isoformat(), 55.0, 72.0))
        cursor.execute("INSERT INTO garden_flowers (task_id, flower_type, color, bloom_date, x_pct, y_pct) VALUES (?, ?, ?, ?, ?, ?)",
                       (None, "lavender", "#c084fc", date.today().isoformat(), 75.0, 60.0))

    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
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

# --- TASKS API ---
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    list_name = request.args.get('list')
    category = request.args.get('category')
    search = request.args.get('search')
    filter_status = request.args.get('status', 'all')  # all, active, completed, archived

    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

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
        # Fetch subtasks
        subtasks_rows = cur.execute(
            "SELECT * FROM subtasks WHERE task_id = ? ORDER BY order_index ASC, id ASC", (t['id'],)
        ).fetchall()
        t['subtasks'] = [dict(s) for s in subtasks_rows]
        result.append(t)
    conn.close()

    return jsonify(result)

@app.route('/api/tasks', methods=['POST'])
def create_task():
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
        INSERT INTO tasks (title, notes, due_date, due_time, priority, category, list_name, is_pinned,
                           recurring, blocked_by_id, time_estimate_minutes, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, notes, due_date, due_time, priority, category, list_name, is_pinned,
          recurring, blocked_by_id, time_estimate_minutes, order_index))

    # Add subtasks if provided
    subtasks = data.get('subtasks', [])
    for idx, s in enumerate(subtasks):
        s_title = s if isinstance(s, str) else s.get('title', '')
        if s_title.strip():
            execute_db('INSERT INTO subtasks (task_id, title, is_completed, order_index) VALUES (?, ?, ?, ?)',
                       (task_id, s_title.strip(), 0, idx))

    created = query_db("SELECT * FROM tasks WHERE id = ?", (task_id,), one=True)
    res = dict(created)
    res['subtasks'] = [dict(s) for s in query_db("SELECT * FROM subtasks WHERE task_id = ?", (task_id,))]
    return jsonify(res), 201

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_single_task(task_id):
    task = query_db("SELECT * FROM tasks WHERE id = ?", (task_id,), one=True)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    res = dict(task)
    res['subtasks'] = [dict(s) for s in query_db("SELECT * FROM subtasks WHERE task_id = ?", (task_id,))]
    return jsonify(res)

@app.route('/api/tasks/<int:task_id>', methods=['PUT', 'PATCH'])
def update_task(task_id):
    task = query_db("SELECT * FROM tasks WHERE id = ?", (task_id,), one=True)
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
        WHERE id=?
    ''', (title, notes, due_date, due_time, priority, category, list_name, is_pinned,
          is_completed, completed_at, is_archived, recurring, blocked_by_id,
          time_estimate_minutes, time_spent_seconds, order_index, task_id))

    # If subtasks array provided, replace
    if 'subtasks' in data:
        execute_db("DELETE FROM subtasks WHERE task_id = ?", (task_id,))
        for idx, s in enumerate(data['subtasks']):
            s_title = s.get('title', '').strip() if isinstance(s, dict) else str(s).strip()
            s_done = 1 if (isinstance(s, dict) and s.get('is_completed')) else 0
            if s_title:
                execute_db("INSERT INTO subtasks (task_id, title, is_completed, order_index) VALUES (?, ?, ?, ?)",
                           (task_id, s_title, s_done, idx))

    # If completed and has recurrence, generate the next task
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
                INSERT INTO tasks (title, notes, due_date, due_time, priority, category, list_name, recurring, time_estimate_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, notes, next_due.isoformat(), due_time, priority, category, list_name, recurring, time_estimate_minutes))
        except Exception:
            pass

    # If just completed, auto-grow a garden flower!
    flower_info = None
    if just_completed:
        # Determine flower type and color based on category
        cat_row = query_db("SELECT color FROM categories WHERE name = ?", (category,), one=True)
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
            INSERT INTO garden_flowers (task_id, flower_type, color, bloom_date, x_pct, y_pct)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (task_id, f_type, flower_color, date.today().isoformat(), rx, ry))
        flower_info = {'id': fid, 'flower_type': f_type, 'color': flower_color, 'x_pct': rx, 'y_pct': ry}

    updated = query_db("SELECT * FROM tasks WHERE id = ?", (task_id,), one=True)
    res = dict(updated)
    res['subtasks'] = [dict(s) for s in query_db("SELECT * FROM subtasks WHERE task_id = ?", (task_id,))]
    res['new_flower'] = flower_info
    return jsonify(res)

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    # Retrieve first to return in case of Undo
    task = query_db("SELECT * FROM tasks WHERE id = ?", (task_id,), one=True)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    t_dict = dict(task)
    t_dict['subtasks'] = [dict(s) for s in query_db("SELECT * FROM subtasks WHERE task_id = ?", (task_id,))]

    execute_db("DELETE FROM subtasks WHERE task_id = ?", (task_id,))
    execute_db("DELETE FROM tasks WHERE id = ?", (task_id,))
    return jsonify({'success': True, 'deleted_task': t_dict})

@app.route('/api/tasks/reorder', methods=['POST'])
def reorder_tasks():
    order_list = request.json.get('task_ids', [])
    for idx, tid in enumerate(order_list):
        execute_db("UPDATE tasks SET order_index = ? WHERE id = ?", (idx, tid))
    return jsonify({'success': True})

@app.route('/api/tasks/bulk', methods=['POST'])
def bulk_actions():
    data = request.json or {}
    task_ids = data.get('task_ids', [])
    action = data.get('action')  # delete, complete, move_list, set_tag, snooze

    if not task_ids:
        return jsonify({'error': 'No tasks provided'}), 400

    conn = get_db()
    cur = conn.cursor()

    if action == 'delete':
        cur.executemany("DELETE FROM subtasks WHERE task_id = ?", [(t,) for t in task_ids])
        cur.executemany("DELETE FROM tasks WHERE id = ?", [(t,) for t in task_ids])
    elif action == 'complete':
        now = datetime.utcnow().isoformat()
        cur.executemany("UPDATE tasks SET is_completed = 1, completed_at = ? WHERE id = ?", [(now, t) for t in task_ids])
    elif action == 'move_list':
        target_list = data.get('list_name', 'Today')
        cur.executemany("UPDATE tasks SET list_name = ? WHERE id = ?", [(target_list, t) for t in task_ids])
    elif action == 'set_tag':
        category = data.get('category', 'Personal')
        cur.executemany("UPDATE tasks SET category = ? WHERE id = ?", [(category, t) for t in task_ids])
    elif action == 'snooze':
        days = int(data.get('days', 1))
        target_date = (date.today() + timedelta(days=days)).isoformat()
        cur.executemany("UPDATE tasks SET due_date = ? WHERE id = ?", [(target_date, t) for t in task_ids])

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'count': len(task_ids)})

@app.route('/api/tasks/<int:task_id>/time', methods=['POST'])
def log_task_time(task_id):
    data = request.json or {}
    additional_seconds = int(data.get('seconds', 0))
    execute_db("UPDATE tasks SET time_spent_seconds = time_spent_seconds + ? WHERE id = ?", (additional_seconds, task_id))
    task = query_db("SELECT id, time_spent_seconds FROM tasks WHERE id = ?", (task_id,), one=True)
    return jsonify(dict(task))

# --- SUBTASKS API ---
@app.route('/api/subtasks/<int:subtask_id>/toggle', methods=['POST'])
def toggle_subtask(subtask_id):
    subtask = query_db("SELECT * FROM subtasks WHERE id = ?", (subtask_id,), one=True)
    if not subtask:
        return jsonify({'error': 'Subtask not found'}), 404
    new_state = 0 if subtask['is_completed'] else 1
    execute_db("UPDATE subtasks SET is_completed = ? WHERE id = ?", (new_state, subtask_id))
    return jsonify({'id': subtask_id, 'is_completed': new_state})

# --- CATEGORIES & LISTS API ---
@app.route('/api/categories', methods=['GET', 'POST'])
def manage_categories():
    if request.method == 'POST':
        name = request.json.get('name', '').strip()
        color = request.json.get('color', '#fbcfe8').strip()
        if not name:
            return jsonify({'error': 'Name required'}), 400
        try:
            cid = execute_db("INSERT INTO categories (name, color) VALUES (?, ?)", (name, color))
            return jsonify({'id': cid, 'name': name, 'color': color}), 201
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Category already exists'}), 409
    cats = query_db("SELECT * FROM categories ORDER BY name ASC")
    return jsonify([dict(c) for c in cats])

@app.route('/api/categories/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    execute_db("DELETE FROM categories WHERE id = ?", (cat_id,))
    return jsonify({'success': True})

@app.route('/api/lists', methods=['GET', 'POST'])
def manage_lists():
    if request.method == 'POST':
        name = request.json.get('name', '').strip()
        icon = request.json.get('icon', '🌸').strip()
        is_locked = 1 if request.json.get('is_locked') else 0
        if not name:
            return jsonify({'error': 'Name required'}), 400
        try:
            lid = execute_db("INSERT INTO lists (name, icon, is_locked) VALUES (?, ?, ?)", (name, icon, is_locked))
            return jsonify({'id': lid, 'name': name, 'icon': icon, 'is_locked': is_locked}), 201
        except sqlite3.IntegrityError:
            return jsonify({'error': 'List already exists'}), 409
    lists = query_db("SELECT * FROM lists ORDER BY id ASC")
    return jsonify([dict(l) for l in lists])

@app.route('/api/lists/<int:list_id>', methods=['DELETE'])
def delete_list(list_id):
    execute_db("DELETE FROM lists WHERE id = ?", (list_id,))
    return jsonify({'success': True})

# --- HABITS API ---
@app.route('/api/habits', methods=['GET', 'POST'])
def manage_habits():
    if request.method == 'POST':
        name = request.json.get('name', '').strip()
        icon = request.json.get('icon', '✨').strip()
        target_days = int(request.json.get('target_days', 7))
        if not name:
            return jsonify({'error': 'Name required'}), 400
        hid = execute_db("INSERT INTO habits (name, icon, target_days, logs_json) VALUES (?, ?, ?, '{}')",
                         (name, icon, target_days))
        return jsonify({'id': hid, 'name': name, 'icon': icon, 'target_days': target_days, 'logs_json': '{}'}), 201

    habits = query_db("SELECT * FROM habits ORDER BY id ASC")
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
def toggle_habit(habit_id):
    habit = query_db("SELECT * FROM habits WHERE id = ?", (habit_id,), one=True)
    if not habit:
        return jsonify({'error': 'Habit not found'}), 404
    date_str = request.json.get('date', date.today().isoformat())
    logs = json.loads(habit['logs_json'] or '{}')

    current_val = logs.get(date_str, False)
    logs[date_str] = not current_val

    execute_db("UPDATE habits SET logs_json = ? WHERE id = ?", (json.dumps(logs), habit_id))
    return jsonify({'id': habit_id, 'date': date_str, 'completed': logs[date_str], 'logs': logs})

@app.route('/api/habits/<int:habit_id>', methods=['DELETE'])
def delete_habit(habit_id):
    execute_db("DELETE FROM habits WHERE id = ?", (habit_id,))
    return jsonify({'success': True})

# --- GOALS API ---
@app.route('/api/goals', methods=['GET', 'POST'])
def manage_goals():
    if request.method == 'POST':
        title = request.json.get('title', '').strip()
        category = request.json.get('category', 'General')
        target_date = request.json.get('target_date', '')
        notes = request.json.get('notes', '')
        if not title:
            return jsonify({'error': 'Title required'}), 400
        gid = execute_db("INSERT INTO goals (title, category, target_date, notes) VALUES (?, ?, ?, ?)",
                         (title, category, target_date, notes))
        return jsonify({'id': gid, 'title': title, 'category': category, 'target_date': target_date, 'notes': notes}), 201
    goals = query_db("SELECT * FROM goals ORDER BY id DESC")
    return jsonify([dict(g) for g in goals])

@app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    execute_db("DELETE FROM goals WHERE id = ?", (goal_id,))
    return jsonify({'success': True})

# --- COUNTDOWNS API ---
@app.route('/api/countdowns', methods=['GET', 'POST'])
def manage_countdowns():
    if request.method == 'POST':
        title = request.json.get('title', '').strip()
        target_date = request.json.get('target_date', '')
        emoji = request.json.get('emoji', '🎉')
        note = request.json.get('note', '')
        if not title or not target_date:
            return jsonify({'error': 'Title and target date required'}), 400
        cid = execute_db("INSERT INTO countdowns (title, target_date, emoji, note) VALUES (?, ?, ?, ?)",
                         (title, target_date, emoji, note))
        return jsonify({'id': cid, 'title': title, 'target_date': target_date, 'emoji': emoji, 'note': note}), 201
    countdowns = query_db("SELECT * FROM countdowns ORDER BY target_date ASC")
    return jsonify([dict(c) for c in countdowns])

@app.route('/api/countdowns/<int:cd_id>', methods=['DELETE'])
def delete_countdown(cd_id):
    execute_db("DELETE FROM countdowns WHERE id = ?", (cd_id,))
    return jsonify({'success': True})

# --- GARDEN & STICKERS & MOODS ---
@app.route('/api/garden', methods=['GET'])
def get_garden():
    flowers = query_db("SELECT * FROM garden_flowers ORDER BY id ASC")
    return jsonify([dict(f) for f in flowers])

@app.route('/api/garden/clear', methods=['POST'])
def clear_garden():
    execute_db("DELETE FROM garden_flowers")
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
def manage_moods():
    if request.method == 'POST':
        date_str = request.json.get('date', date.today().isoformat())
        mood_emoji = request.json.get('mood_emoji', '🌸')
        note = request.json.get('note', '')
        execute_db('''
            INSERT INTO mood_logs (date_str, mood_emoji, note) VALUES (?, ?, ?)
            ON CONFLICT(date_str) DO UPDATE SET mood_emoji=excluded.mood_emoji, note=excluded.note
        ''', (date_str, mood_emoji, note))
        return jsonify({'date_str': date_str, 'mood_emoji': mood_emoji, 'note': note})
    moods = query_db("SELECT * FROM mood_logs ORDER BY date_str DESC LIMIT 30")
    return jsonify([dict(m) for m in moods])

# --- STATS & INSIGHTS ---
@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    cur = conn.cursor()

    total_tasks = cur.execute("SELECT COUNT(*) FROM tasks WHERE is_archived = 0").fetchone()[0]
    completed_tasks = cur.execute("SELECT COUNT(*) FROM tasks WHERE is_completed = 1 AND is_archived = 0").fetchone()[0]
    archived_tasks = cur.execute("SELECT COUNT(*) FROM tasks WHERE is_archived = 1").fetchone()[0]
    completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)

    # Category breakdown
    cat_counts = cur.execute('''
        SELECT category, COUNT(*) as count FROM tasks WHERE is_archived = 0 GROUP BY category
    ''').fetchall()
    cat_breakdown = {row['category']: row['count'] for row in cat_counts}

    # Time tracking total
    time_spent_total = cur.execute("SELECT COALESCE(SUM(time_spent_seconds), 0) FROM tasks").fetchone()[0]
    time_estimate_total = cur.execute("SELECT COALESCE(SUM(time_estimate_minutes), 0) FROM tasks WHERE is_completed = 0").fetchone()[0]

    # Weekly history (last 7 days completed tasks)
    today = date.today()
    weekly_activity = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        count = cur.execute('''
            SELECT COUNT(*) FROM tasks WHERE completed_at LIKE ? AND is_completed = 1
        ''', (f"{day_str}%",)).fetchone()[0]
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
def drop_template(tpl_type):
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
            INSERT INTO tasks (title, notes, priority, category, due_date, time_estimate_minutes, list_name)
            VALUES (?, ?, ?, ?, ?, ?, 'Today')
        ''', (item[0], item[1], item[2], item[3], today_str, item[4]))
        created.append(tid)

    return jsonify({'success': True, 'count': len(created)})

# --- AUTH & SECURITY API ---
@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    p_hash = query_db("SELECT value FROM settings WHERE key = 'password_hash'", one=True)
    hint = query_db("SELECT value FROM settings WHERE key = 'password_hint'", one=True)
    auto_lock = query_db("SELECT value FROM settings WHERE key = 'auto_lock_mins'", one=True)
    lock_blur = query_db("SELECT value FROM settings WHERE key = 'lock_on_blur'", one=True)

    return jsonify({
        'is_setup': bool(p_hash and p_hash['value']),
        'hint': hint['value'] if hint else '',
        'auto_lock_mins': int(auto_lock['value']) if auto_lock else 5,
        'lock_on_blur': int(lock_blur['value']) if lock_blur else 0
    })

@app.route('/api/auth/setup', methods=['POST'])
def auth_setup():
    p_hash = query_db("SELECT value FROM settings WHERE key = 'password_hash'", one=True)
    if p_hash and p_hash['value']:
        return jsonify({'error': 'Password already configured. Use change password.'}), 400

    password = request.json.get('password', '').strip()
    hint = request.json.get('hint', '').strip()

    if not password or len(password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400

    hashed = generate_password_hash(password)
    execute_db("INSERT OR REPLACE INTO settings (key, value) VALUES ('password_hash', ?)", (hashed,))
    execute_db("INSERT OR REPLACE INTO settings (key, value) VALUES ('password_hint', ?)", (hint,))
    return jsonify({'success': True})

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    p_hash = query_db("SELECT value FROM settings WHERE key = 'password_hash'", one=True)
    if not p_hash or not p_hash['value']:
        return jsonify({'success': True, 'notice': 'No password set'})

    password = request.json.get('password', '')
    if check_password_hash(p_hash['value'], password):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Incorrect password'}), 401

@app.route('/api/auth/change_password', methods=['POST'])
def auth_change():
    p_hash = query_db("SELECT value FROM settings WHERE key = 'password_hash'", one=True)
    old_pw = request.json.get('old_password', '')
    new_pw = request.json.get('new_password', '').strip()
    hint = request.json.get('hint', '').strip()

    if p_hash and p_hash['value']:
        if not check_password_hash(p_hash['value'], old_pw):
            return jsonify({'error': 'Current password incorrect'}), 401

    if not new_pw or len(new_pw) < 4:
        return jsonify({'error': 'New password must be at least 4 characters'}), 400

    hashed = generate_password_hash(new_pw)
    execute_db("INSERT OR REPLACE INTO settings (key, value) VALUES ('password_hash', ?)", (hashed,))
    if hint:
        execute_db("INSERT OR REPLACE INTO settings (key, value) VALUES ('password_hint', ?)", (hint,))
    return jsonify({'success': True})

# --- SETTINGS API ---
@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    if request.method == 'POST':
        data = request.json or {}
        conn = get_db()
        cur = conn.cursor()
        for k, v in data.items():
            if k != 'password_hash':  # protected
                cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    settings_rows = query_db("SELECT key, value FROM settings WHERE key != 'password_hash'")
    return jsonify({r['key']: r['value'] for r in settings_rows})

# --- DATA EXPORT & IMPORT ---
@app.route('/api/export', methods=['GET'])
def export_data():
    fmt = request.args.get('format', 'json').lower()
    conn = get_db()
    cur = conn.cursor()

    tasks = [dict(r) for r in cur.execute("SELECT * FROM tasks").fetchall()]
    for t in tasks:
        t['subtasks'] = [dict(s) for s in cur.execute("SELECT * FROM subtasks WHERE task_id = ?", (t['id'],)).fetchall()]

    habits = [dict(r) for r in cur.execute("SELECT * FROM habits").fetchall()]
    goals = [dict(r) for r in cur.execute("SELECT * FROM goals").fetchall()]
    categories = [dict(r) for r in cur.execute("SELECT * FROM categories").fetchall()]
    lists = [dict(r) for r in cur.execute("SELECT * FROM lists").fetchall()]
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
def import_data():
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
                    INSERT INTO tasks (title, notes, due_date, due_time, priority, category, list_name,
                                       is_pinned, is_completed, recurring, time_estimate_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (t.get('title', 'Imported Task'), t.get('notes', ''), t.get('due_date', ''),
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
            if idx > 25:  # limit to first 25 pages for speed and token limits
                break
            extracted = page.extract_text()
            if extracted:
                text_content += extracted + "\n"

        text_content = text_content.strip()
        if not text_content:
            return jsonify({'error': 'No readable text could be extracted from this PDF. It may be a scanned image or protected.'}), 400

        api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()

        # If Anthropic API key is available, call Anthropic API
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
                # Extract JSON if enclosed in markdown blocks
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
            except Exception as anthropic_err:
                # Fallback to local heuristic parser if API call fails
                pass

        # Smart built-in heuristic extractor when no API key or error
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
            # Fallback tasks from top sections
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
def send_email_summary():
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
    pending = cur.execute("SELECT title, priority, due_time FROM tasks WHERE is_completed = 0 AND due_date = ?", (today_str,)).fetchall()
    completed = cur.execute("SELECT title FROM tasks WHERE is_completed = 1 AND completed_at LIKE ?", (f"{today_str}%",)).fetchall()
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
