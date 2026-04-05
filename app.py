"""
Professional Typing Test Application with Admin Panel
Features: Multiple time options, Admin management, Adaptive difficulty
"""

import os
import secrets
import sqlite3
import statistics
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
from functools import wraps
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['JSON_SORT_KEYS'] = False

# Admin credentials (change these in production)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Time options (in seconds)
TIME_OPTIONS = [15, 30, 60, 120, 300]  # 15s, 30s, 1min, 2min, 5min

# ==================== DATABASE SETUP ====================
def get_db():
    db_path = os.environ.get('DATABASE_PATH', 'typingtest.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def db_connection():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    with db_connection() as conn:
        # Test results table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                wpm REAL NOT NULL,
                accuracy REAL NOT NULL,
                level INTEGER NOT NULL,
                time_mode INTEGER NOT NULL,
                text_length INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                mistakes INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Custom texts table for admin
        conn.execute('''
            CREATE TABLE IF NOT EXISTS custom_texts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Admin settings table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default settings
        conn.execute('''
            INSERT OR IGNORE INTO admin_settings (key, value) VALUES 
            ('site_title', 'TypeMaster Pro'),
            ('site_subtitle', 'Professional Adaptive Typing Test'),
            ('default_time_mode', '60'),
            ('enable_adaptive_level', 'true'),
            ('require_login', 'false')
        ''')
        
        conn.execute('CREATE INDEX IF NOT EXISTS idx_results_session ON test_results(session_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_results_date ON test_results(created_at)')

init_database()

# ==================== DEFAULT TEXTS ====================
DEFAULT_TEXTS = {
    1: [
        "The quick brown fox jumps over the lazy dog. Practice makes perfect when learning to type quickly. Start with simple sentences and gradually increase difficulty. Focus on proper finger placement and ergonomic posture.",
        "Technology has transformed how we communicate across the globe. Modern devices make it easier to connect with people worldwide. Typing has become an essential skill in the digital age.",
        "Success is not final, failure is not fatal: it is the courage to continue that counts. Keep practicing your typing skills every single day. Small consistent efforts lead to remarkable improvements."
    ],
    2: [
        "Artificial intelligence and machine learning are revolutionizing industries worldwide. These technologies enable computers to learn from experience and perform complex tasks. Neural networks can now recognize patterns with remarkable accuracy.",
        "The human brain processes visual information incredibly fast, but reading and typing require coordination between eyes, hands, and cognitive functions. Regular practice strengthens neural pathways significantly.",
        "Sustainable development aims to meet present needs without compromising future generations. This involves balancing economic growth with environmental protection."
    ],
    3: [
        "Quantum computing leverages quantum mechanical phenomena such as superposition and entanglement to perform calculations exponentially faster than classical computers. This technology could transform cryptography and drug discovery.",
        "The intricate dance of neural networks in deep learning architectures mimics biological brain structures. These systems enable breakthrough applications in computer vision and natural language processing.",
        "Blockchain technology provides decentralized consensus mechanisms that ensure data integrity without trusted third parties. This innovation powers cryptocurrencies and smart contracts."
    ],
    4: [
        "Neuroplasticity demonstrates that our brains remain adaptable throughout life, forming new neural connections in response to learning and experience. This property underlies cognitive rehabilitation and skill acquisition.",
        "The philosophical implications of consciousness in artificial systems raise profound questions about sentience and morality. As AI systems become sophisticated, we must consider ethical frameworks."
    ],
    5: [
        "The synthesis of advanced materials at nanoscale dimensions exhibits extraordinary quantum effects. These semiconductor nanocrystals enable next-generation display technologies and quantum information processing.",
        "Complex adaptive systems theory explains how emergent behaviors arise from simple local interactions. This framework applies to ecosystems, financial markets, and social networks."
    ]
}

def get_text_for_level(level):
    """Get text from custom texts first, then defaults"""
    level = max(1, min(level, 5))
    
    with db_connection() as conn:
        custom = conn.execute(
            'SELECT content FROM custom_texts WHERE level = ? AND is_active = 1 ORDER BY id DESC LIMIT 1',
            (level,)
        ).fetchone()
        
        if custom:
            return {'text': custom['content'], 'length': len(custom['content']), 'level': level}
    
    # Fallback to defaults
    texts = DEFAULT_TEXTS.get(level, DEFAULT_TEXTS[5])
    import random
    text = random.choice(texts)
    return {'text': text, 'length': len(text), 'level': level}

# ==================== HELPER FUNCTIONS ====================
def get_or_create_session():
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(16)
        session.permanent = True
    return session['session_id']

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== MAIN ROUTES ====================
@app.route('/')
def index():
    get_or_create_session()
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TypeMaster Pro | Professional Typing Test</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 20px 30px;
            margin-bottom: 25px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .logo h1 {
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 28px;
        }
        .admin-link {
            background: #667eea;
            color: white;
            padding: 8px 16px;
            border-radius: 10px;
            text-decoration: none;
            font-size: 14px;
        }
        .stats { display: flex; gap: 20px; flex-wrap: wrap; }
        .stat-card {
            text-align: center;
            padding: 10px 20px;
            background: #f8f9fa;
            border-radius: 15px;
            min-width: 100px;
        }
        .stat-value { font-size: 28px; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 12px; color: #666; margin-top: 5px; }
        .test-area {
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .level-badge {
            display: inline-block;
            padding: 8px 20px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border-radius: 25px;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .time-selector {
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .time-btn {
            padding: 8px 20px;
            border: 2px solid #667eea;
            background: white;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .time-btn.active {
            background: #667eea;
            color: white;
        }
        .time-btn:hover { transform: translateY(-2px); }
        .timer-display {
            font-size: 36px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 20px;
            font-family: monospace;
        }
        .text-display {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 15px;
            font-size: 18px;
            line-height: 1.6;
            margin-bottom: 20px;
            font-family: 'Courier New', monospace;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .text-display span.correct { color: #28a745; background: #d4edda; }
        .text-display span.incorrect { color: #dc3545; background: #f8d7da; text-decoration: underline; }
        .text-display span.current { background: #ffc107; }
        .typing-input {
            width: 100%;
            padding: 20px;
            font-size: 16px;
            font-family: 'Courier New', monospace;
            border: 2px solid #ddd;
            border-radius: 15px;
            resize: vertical;
            margin-bottom: 20px;
        }
        .typing-input:focus { outline: none; border-color: #667eea; }
        .progress-bar {
            height: 10px;
            background: #e0e0e0;
            border-radius: 5px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s;
            width: 0%;
        }
        .controls { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
            font-weight: bold;
        }
        .btn:hover { transform: translateY(-2px); }
        .btn-primary { background: #667eea; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-success { background: #28a745; color: white; }
        .results {
            background: white;
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 15px;
        }
        .metric-value { font-size: 36px; font-weight: bold; color: #667eea; }
        .metric-label { color: #666; margin-top: 10px; }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #ddd;
        }
        th { background: #667eea; color: white; }
        @media (max-width: 768px) {
            .stats { margin-top: 15px; width: 100%; justify-content: space-between; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo"><h1>⚡ TypeMaster Pro</h1><p>Professional Adaptive Typing Test</p></div>
            <a href="/admin" class="admin-link">🔧 Admin Panel</a>
        </div>
        
        <div class="test-area">
            <div class="level-badge" id="levelBadge">🔥 LEVEL 1 - BEGINNER</div>
            <div class="time-selector" id="timeSelector"></div>
            <div class="timer-display" id="timerDisplay">60s</div>
            <div class="text-display" id="textDisplay"></div>
            <textarea class="typing-input" id="typingInput" rows="4" placeholder="Select time and click START..." disabled></textarea>
            <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
            <div class="controls">
                <button class="btn btn-primary" id="startBtn">▶ START TEST</button>
                <button class="btn btn-danger" id="resetBtn">⟳ RESET</button>
            </div>
        </div>
        
        <div class="results" id="resultsPanel" style="display: none;">
            <h2>📊 Test Results</h2>
            <div class="metrics" id="resultMetrics"></div>
            <h3>📜 Test History</h3>
            <div style="overflow-x: auto;"><table><thead><tr><th>Date</th><th>WPM</th><th>Accuracy</th><th>Level</th><th>Time Mode</th><th>Mistakes</th></tr></thead><tbody id="historyBody"></tbody></table></div>
        </div>
        
        <div class="stats" style="justify-content: center; margin-top: 20px;">
            <div class="stat-card"><div class="stat-value" id="statWPM">0</div><div class="stat-label">Current WPM</div></div>
            <div class="stat-card"><div class="stat-value" id="statAccuracy">100</div><div class="stat-label">Accuracy %</div></div>
            <div class="stat-card"><div class="stat-value" id="statLevel">1</div><div class="stat-label">Level</div></div>
        </div>
    </div>
    
    <script>
        let currentText = '', currentLevel = 1, currentTimeMode = 60;
        let testActive = false, startTime = null, timeRemaining = 60;
        let currentInput = '', mistakes = 0, totalTyped = 0, correctTyped = 0;
        let timerInterval = null, countdownInterval = null;
        
        const timeOptions = [15, 30, 60, 120, 300];
        
        function initTimeSelector() {
            const container = document.getElementById('timeSelector');
            container.innerHTML = timeOptions.map(t => `
                <button class="time-btn ${t === 60 ? 'active' : ''}" data-time="${t}">
                    ${t < 60 ? t + 's' : (t === 60 ? '1 min' : (t === 120 ? '2 min' : '5 min'))}
                </button>
            `).join('');
            
            document.querySelectorAll('.time-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    currentTimeMode = parseInt(btn.dataset.time);
                    document.getElementById('timerDisplay').innerText = formatTime(currentTimeMode);
                });
            });
        }
        
        function formatTime(seconds) {
            if (seconds < 60) return seconds + 's';
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return secs > 0 ? `${mins}m ${secs}s` : `${mins} min`;
        }
        
        async function loadText() {
            const response = await fetch('/api/get_text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ level: currentLevel })
            });
            const data = await response.json();
            currentText = data.text;
            updateTextDisplay();
        }
        
        function updateTextDisplay() {
            if (!currentText) return;
            let html = '';
            for (let i = 0; i < currentText.length; i++) {
                let charClass = '';
                if (i < currentInput.length) {
                    charClass = currentInput[i] === currentText[i] ? 'correct' : 'incorrect';
                } else if (i === currentInput.length && testActive) {
                    charClass = 'current';
                }
                let char = currentText[i];
                if (char === ' ') char = '&nbsp;';
                html += `<span class="${charClass}">${char}</span>`;
            }
            document.getElementById('textDisplay').innerHTML = html;
            let progress = (currentInput.length / currentText.length) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
        }
        
        function updateLiveStats() {
            if (!testActive || !startTime) return;
            const elapsed = (Date.now() - startTime) / 1000;
            const timeUsed = currentTimeMode - timeRemaining;
            if (timeUsed > 0 && totalTyped > 0) {
                const wpm = Math.round((correctTyped / 5) / (timeUsed / 60));
                const accuracy = Math.round((correctTyped / totalTyped) * 100);
                document.getElementById('statWPM').textContent = wpm;
                document.getElementById('statAccuracy').textContent = accuracy;
            }
        }
        
        function startCountdown() {
            timeRemaining = currentTimeMode;
            document.getElementById('timerDisplay').innerHTML = formatTime(timeRemaining);
            if (countdownInterval) clearInterval(countdownInterval);
            countdownInterval = setInterval(() => {
                if (!testActive) return;
                if (timeRemaining <= 0) {
                    endTest();
                } else {
                    timeRemaining--;
                    document.getElementById('timerDisplay').innerHTML = formatTime(timeRemaining);
                }
            }, 1000);
        }
        
        function startTest() {
            if (testActive) return;
            testActive = true;
            startTime = Date.now();
            currentInput = '';
            mistakes = 0;
            totalTyped = 0;
            correctTyped = 0;
            document.getElementById('typingInput').disabled = false;
            document.getElementById('typingInput').value = '';
            document.getElementById('typingInput').focus();
            updateTextDisplay();
            startCountdown();
            timerInterval = setInterval(() => {
                updateLiveStats();
            }, 100);
        }
        
        async function endTest() {
            if (!testActive) return;
            testActive = false;
            clearInterval(timerInterval);
            clearInterval(countdownInterval);
            
            const timeUsed = currentTimeMode - timeRemaining;
            const wpm = timeUsed > 0 ? Math.round((correctTyped / 5) / (timeUsed / 60)) : 0;
            const accuracy = totalTyped > 0 ? Math.round((correctTyped / totalTyped) * 100) : 100;
            
            await fetch('/api/submit_result', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    wpm: wpm,
                    accuracy: accuracy,
                    level: currentLevel,
                    time_mode: currentTimeMode,
                    text_length: currentText.length,
                    time_taken: timeUsed,
                    mistakes: mistakes
                })
            });
            
            await loadHistory();
            document.getElementById('resultsPanel').style.display = 'block';
            document.getElementById('resultMetrics').innerHTML = `
                <div class="metric"><div class="metric-value">${wpm}</div><div class="metric-label">WPM</div></div>
                <div class="metric"><div class="metric-value">${accuracy}%</div><div class="metric-label">Accuracy</div></div>
                <div class="metric"><div class="metric-value">${Math.floor(timeUsed)}s</div><div class="metric-label">Time Used</div></div>
                <div class="metric"><div class="metric-value">${mistakes}</div><div class="metric-label">Mistakes</div></div>
            `;
            document.getElementById('typingInput').disabled = true;
        }
        
        async function loadHistory() {
            const response = await fetch('/api/get_history');
            const data = await response.json();
            const tbody = document.getElementById('historyBody');
            if (data.history && data.history.length > 0) {
                tbody.innerHTML = data.history.map(h => `
                    <tr>
                        <td>${h.date}</td>
                        <td>${h.wpm}</td>
                        <td>${h.accuracy}%</td>
                        <td>${h.level}</td>
                        <td>${h.time_mode}s</td>
                        <td>${h.mistakes}</td>
                    </tr>
                `).join('');
            }
        }
        
        function resetTest() {
            if (testActive) {
                testActive = false;
                clearInterval(timerInterval);
                clearInterval(countdownInterval);
            }
            document.getElementById('typingInput').disabled = true;
            document.getElementById('typingInput').value = '';
            currentInput = '';
            timeRemaining = currentTimeMode;
            document.getElementById('timerDisplay').innerHTML = formatTime(currentTimeMode);
            document.getElementById('statWPM').textContent = '0';
            document.getElementById('statAccuracy').textContent = '100';
            loadText();
        }
        
        document.getElementById('typingInput').addEventListener('input', (e) => {
            if (!testActive) return;
            const newValue = e.target.value;
            const newLength = newValue.length;
            const oldLength = currentInput.length;
            
            for (let i = oldLength; i < newLength && i < currentText.length; i++) {
                totalTyped++;
                if (newValue[i] === currentText[i]) {
                    correctTyped++;
                } else {
                    mistakes++;
                }
            }
            
            if (newLength < oldLength) {
                correctTyped = 0;
                mistakes = 0;
                totalTyped = 0;
                for (let i = 0; i < newLength && i < currentText.length; i++) {
                    totalTyped++;
                    if (newValue[i] === currentText[i]) correctTyped++;
                    else mistakes++;
                }
            }
            
            currentInput = newValue;
            updateTextDisplay();
            updateLiveStats();
        });
        
        document.getElementById('startBtn').addEventListener('click', () => { resetTest(); startTest(); });
        document.getElementById('resetBtn').addEventListener('click', resetTest);
        
        initTimeSelector();
        loadText();
        loadHistory();
        
        setInterval(async () => {
            const resp = await fetch('/api/get_level');
            const data = await resp.json();
            if (data.level !== currentLevel) {
                currentLevel = data.level;
                document.getElementById('statLevel').textContent = currentLevel;
                const levelNames = {1:'BEGINNER',2:'INTERMEDIATE',3:'ADVANCED',4:'EXPERT',5:'MASTER'};
                document.getElementById('levelBadge').innerHTML = `🔥 LEVEL ${currentLevel} - ${levelNames[currentLevel] || 'PRO'}`;
                loadText();
            }
        }, 3000);
    </script>
</body>
</html>'''
    return render_template_string(html_content)

# ==================== ADMIN PANEL ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template_string(ADMIN_LOGIN_HTML, error='Invalid credentials')
    return render_template_string(ADMIN_LOGIN_HTML, error=None)

ADMIN_LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            width: 350px;
        }
        h2 { text-align: center; color: #667eea; margin-bottom: 30px; }
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        .error { color: red; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔧 Admin Login</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
    </div>
</body>
</html>
'''

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template_string(ADMIN_DASHBOARD_HTML)

ADMIN_DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Admin Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #f5f5f5;
            font-family: sans-serif;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logout-btn {
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 8px;
            color: white;
            text-decoration: none;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 12px 24px;
            background: white;
            border: none;
            cursor: pointer;
            border-radius: 10px;
            font-size: 16px;
        }
        .tab.active {
            background: #667eea;
            color: white;
        }
        .tab-content {
            background: white;
            padding: 25px;
            border-radius: 15px;
            display: none;
        }
        .tab-content.active { display: block; }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        select, textarea, input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        textarea { min-height: 200px; font-family: monospace; }
        button {
            background: #28a745;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover { opacity: 0.9; }
        .success {
            background: #d4edda;
            color: #155724;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .text-list {
            margin-top: 20px;
        }
        .text-item {
            background: #f8f9fa;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .delete-btn {
            background: #dc3545;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }
        .stat-number {
            font-size: 36px;
            font-weight: bold;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th { background: #f8f9fa; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 Admin Dashboard</h1>
            <a href="/admin/logout" class="logout-btn">Logout</a>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('manage')">📝 Manage Texts</button>
            <button class="tab" onclick="showTab('stats')">📊 Statistics</button>
            <button class="tab" onclick="showTab('settings')">⚙️ Settings</button>
        </div>
        
        <div id="manage" class="tab-content active">
            <h2>Add/Edit Typing Text</h2>
            <form id="addTextForm">
                <div class="form-group">
                    <label>Level (1-5):</label>
                    <select name="level" required>
                        <option value="1">Level 1 - Beginner</option>
                        <option value="2">Level 2 - Intermediate</option>
                        <option value="3">Level 3 - Advanced</option>
                        <option value="4">Level 4 - Expert</option>
                        <option value="5">Level 5 - Master</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Title:</label>
                    <input type="text" name="title" placeholder="Text title" required>
                </div>
                <div class="form-group">
                    <label>Content (minimum 500 characters recommended):</label>
                    <textarea name="content" placeholder="Enter your typing test text here..." required></textarea>
                </div>
                <button type="submit">➕ Add Text</button>
            </form>
            <div id="message"></div>
            <div class="text-list" id="textList"></div>
        </div>
        
        <div id="stats" class="tab-content">
            <div class="stats-grid" id="statsGrid"></div>
            <h3>Recent Tests</h3>
            <div style="overflow-x: auto;"><table id="recentTestsTable"><thead><tr><th>Date</th><th>WPM</th><th>Accuracy</th><th>Level</th><th>Time Mode</th></tr></thead><tbody id="recentTestsBody"></tbody></table></div>
        </div>
        
        <div id="settings" class="tab-content">
            <h2>Site Settings</h2>
            <form id="settingsForm">
                <div class="form-group">
                    <label>Site Title:</label>
                    <input type="text" name="site_title" id="site_title">
                </div>
                <div class="form-group">
                    <label>Default Time Mode (seconds):</label>
                    <select name="default_time_mode" id="default_time_mode">
                        <option value="15">15 seconds</option>
                        <option value="30">30 seconds</option>
                        <option value="60">60 seconds</option>
                        <option value="120">2 minutes</option>
                        <option value="300">5 minutes</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" name="enable_adaptive_level" id="enable_adaptive_level">
                        Enable Adaptive Difficulty
                    </label>
                </div>
                <button type="submit">💾 Save Settings</button>
            </form>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }
        
        document.getElementById('addTextForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/admin/api/add_text', {
                method: 'POST',
                body: JSON.stringify(Object.fromEntries(formData)),
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            document.getElementById('message').innerHTML = `<div class="success">${data.message}</div>`;
            e.target.reset();
            loadTexts();
            setTimeout(() => document.getElementById('message').innerHTML = '', 3000);
        });
        
        async function loadTexts() {
            const response = await fetch('/admin/api/get_texts');
            const texts = await response.json();
            const container = document.getElementById('textList');
            container.innerHTML = '<h3>Existing Texts</h3>' + texts.map(t => `
                <div class="text-item">
                    <strong>Level ${t.level}: ${t.title}</strong><br>
                    <small>Added: ${t.created_at}</small><br>
                    <p>${t.content.substring(0, 200)}...</p>
                    <button class="delete-btn" onclick="deleteText(${t.id})">Delete</button>
                </div>
            `).join('');
        }
        
        async function deleteText(id) {
            if (confirm('Delete this text?')) {
                await fetch('/admin/api/delete_text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id })
                });
                loadTexts();
            }
        }
        
        async function loadStats() {
            const response = await fetch('/admin/api/stats');
            const stats = await response.json();
            document.getElementById('statsGrid').innerHTML = `
                <div class="stat-card"><div class="stat-number">${stats.total_tests}</div><div>Total Tests</div></div>
                <div class="stat-card"><div class="stat-number">${stats.avg_wpm}</div><div>Avg WPM</div></div>
                <div class="stat-card"><div class="stat-number">${stats.best_wpm}</div><div>Best WPM</div></div>
                <div class="stat-card"><div class="stat-number">${stats.total_users}</div><div>Active Users</div></div>
            `;
            document.getElementById('recentTestsBody').innerHTML = stats.recent_tests.map(t => `
                <tr><td>${t.date}</td><td>${t.wpm}</td><td>${t.accuracy}%</td><td>${t.level}</td><td>${t.time_mode}s</td></tr>
            `).join('');
        }
        
        async function loadSettings() {
            const response = await fetch('/admin/api/get_settings');
            const settings = await response.json();
            document.getElementById('site_title').value = settings.site_title;
            document.getElementById('default_time_mode').value = settings.default_time_mode;
            document.getElementById('enable_adaptive_level').checked = settings.enable_adaptive_level === 'true';
        }
        
        document.getElementById('settingsForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = {
                site_title: document.getElementById('site_title').value,
                default_time_mode: document.getElementById('default_time_mode').value,
                enable_adaptive_level: document.getElementById('enable_adaptive_level').checked ? 'true' : 'false'
            };
            await fetch('/admin/api/save_settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            alert('Settings saved!');
        });
        
        loadTexts();
        loadStats();
        loadSettings();
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
'''

@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# ==================== ADMIN API ROUTES ====================
@app.route('/admin/api/add_text', methods=['POST'])
@admin_required
def admin_add_text():
    data = request.get_json()
    with db_connection() as conn:
        conn.execute(
            'INSERT INTO custom_texts (level, title, content) VALUES (?, ?, ?)',
            (data['level'], data['title'], data['content'])
        )
    return jsonify({'message': 'Text added successfully!'})

@app.route('/admin/api/get_texts', methods=['GET'])
@admin_required
def admin_get_texts():
    with db_connection() as conn:
        texts = conn.execute('SELECT * FROM custom_texts ORDER BY level, id DESC').fetchall()
    return jsonify([dict(t) for t in texts])

@app.route('/admin/api/delete_text', methods=['POST'])
@admin_required
def admin_delete_text():
    data = request.get_json()
    with db_connection() as conn:
        conn.execute('DELETE FROM custom_texts WHERE id = ?', (data['id'],))
    return jsonify({'message': 'Deleted'})

@app.route('/admin/api/stats', methods=['GET'])
@admin_required
def admin_stats():
    with db_connection() as conn:
        total_tests = conn.execute('SELECT COUNT(*) as count FROM test_results').fetchone()['count']
        avg_wpm = conn.execute('SELECT AVG(wpm) as avg FROM test_results').fetchone()['avg']
        best_wpm = conn.execute('SELECT MAX(wpm) as best FROM test_results').fetchone()['best']
        total_users = conn.execute('SELECT COUNT(DISTINCT session_id) as count FROM test_results').fetchone()['count']
        recent_tests = conn.execute('''
            SELECT wpm, accuracy, level, time_mode, datetime(created_at, 'localtime') as date 
            FROM test_results ORDER BY created_at DESC LIMIT 10
        ''').fetchall()
    
    return jsonify({
        'total_tests': total_tests or 0,
        'avg_wpm': round(avg_wpm or 0, 1),
        'best_wpm': round(best_wpm or 0, 1),
        'total_users': total_users or 0,
        'recent_tests': [dict(t) for t in recent_tests]
    })

@app.route('/admin/api/get_settings', methods=['GET'])
@admin_required
def admin_get_settings():
    with db_connection() as conn:
        settings = {row['key']: row['value'] for row in conn.execute('SELECT key, value FROM admin_settings').fetchall()}
    return jsonify(settings)

@app.route('/admin/api/save_settings', methods=['POST'])
@admin_required
def admin_save_settings():
    data = request.get_json()
    with db_connection() as conn:
        for key, value in data.items():
            conn.execute('UPDATE admin_settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?', (value, key))
    return jsonify({'message': 'Settings saved'})

# ==================== USER API ROUTES ====================
@app.route('/api/get_text', methods=['POST'])
def api_get_text():
    data = request.get_json()
    level = data.get('level', 1)
    return jsonify(get_text_for_level(level))

@app.route('/api/submit_result', methods=['POST'])
def api_submit_result():
    session_id = get_or_create_session()
    data = request.get_json()
    with db_connection() as conn:
        conn.execute('''
            INSERT INTO test_results (session_id, wpm, accuracy, level, time_mode, text_length, time_taken, mistakes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, data.get('wpm'), data.get('accuracy'), data.get('level'), 
              data.get('time_mode'), data.get('text_length'), data.get('time_taken'), data.get('mistakes')))
    return jsonify({'status': 'success'})

@app.route('/api/get_history', methods=['GET'])
def api_get_history():
    session_id = get_or_create_session()
    with db_connection() as conn:
        results = conn.execute('''
            SELECT wpm, accuracy, level, time_mode, mistakes, 
                   datetime(created_at, 'localtime') as date
            FROM test_results WHERE session_id = ? ORDER BY created_at DESC LIMIT 50
        ''', (session_id,)).fetchall()
    return jsonify({'history': [dict(r) for r in results]})

@app.route('/api/get_level', methods=['GET'])
def api_get_level():
    session_id = get_or_create_session()
    with db_connection() as conn:
        results = conn.execute('''
            SELECT wpm, accuracy FROM test_results 
            WHERE session_id = ? ORDER BY created_at DESC LIMIT 5
        ''', (session_id,)).fetchall()
        
        current_level = 1
        if results:
            avg_wpm = statistics.mean([r['wpm'] for r in results])
            avg_acc = statistics.mean([r['accuracy'] for r in results])
            if avg_wpm >= 60 and avg_acc >= 92: current_level = 5
            elif avg_wpm >= 45 and avg_acc >= 88: current_level = 4
            elif avg_wpm >= 30 and avg_acc >= 85: current_level = 3
            elif avg_wpm >= 20 and avg_acc >= 80: current_level = 2
    return jsonify({'level': current_level})

# ==================== MAIN ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
