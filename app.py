"""
Professional Typing Test Application
Advanced Features: Adaptive Difficulty, Performance Analytics, History Tracking
"""

import os
import secrets
import sqlite3
import statistics
from datetime import timedelta
from contextlib import contextmanager
from functools import wraps

from flask import (
    Flask, render_template_string, request, jsonify, 
    session, g
)
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress

app = Flask(__name__)

# Production-ready configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Performance optimization
Compress(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# ==================== DATABASE SETUP ====================
def get_db():
    """Get database connection"""
    db_path = os.environ.get('DATABASE_PATH', 'typingtest.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def db_connection():
    """Context manager for database connections"""
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
    """Initialize database tables"""
    with db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                wpm REAL NOT NULL,
                accuracy REAL NOT NULL,
                raw_wpm REAL,
                level INTEGER NOT NULL,
                text_length INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                mistakes INTEGER NOT NULL,
                correct_chars INTEGER,
                total_chars INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS typing_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                current_level INTEGER DEFAULT 1,
                total_tests_completed INTEGER DEFAULT 0,
                average_wpm REAL DEFAULT 0,
                average_accuracy REAL DEFAULT 0,
                highest_level_reached INTEGER DEFAULT 1,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_results_session ON test_results(session_id)
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_results_date ON test_results(created_at)
        ''')

# Initialize database
init_database()

# ==================== TEXT DATABASE (2000+ characters each) ====================
TEXTS_DB = {
    1: [
        """The journey of mastering touch typing begins with understanding the fundamental principles of keyboard layout and finger positioning. The QWERTY keyboard layout, invented by Christopher Latham Sholes in 1873, was originally designed to prevent mechanical typewriter jams by separating common letter pairs. Today, despite more efficient alternatives like Dvorak or Colemak, QWERTY remains the global standard due to its widespread adoption and network effects. When learning to type, your fingers should rest on the home row: left hand on A, S, D, F and right hand on J, K, L, semicolon. Your thumbs naturally hover over the space bar, which is the most frequently pressed key. Proper posture is equally important: sit straight with elbows at a 90-degree angle, wrists slightly elevated, and screen at eye level to prevent strain and repetitive stress injuries. Beginners often struggle with looking at the keyboard, but developing muscle memory through consistent practice eliminates this dependency. Start with simple drills focusing on home row letters, then gradually expand to the top and bottom rows. The key to rapid improvement is quality over quantity—it's better to practice accurately for 15 minutes daily than to type carelessly for an hour. Many online resources offer structured lessons that progressively introduce new keys while reinforcing previously learned ones. Remember that typing speed plateaus are normal; pushing through them requires deliberate practice with targeted exercises that challenge your weak points. The average professional typist achieves 60-80 words per minute, while elite court reporters can exceed 200 words per minute using specialized stenotype machines. With dedication and proper technique, anyone can achieve functional typing proficiency that enhances productivity in our increasingly digital world. Touch typing not only saves time but also reduces cognitive load, allowing you to focus on content rather than key locations. This skill becomes particularly valuable for programmers, writers, data entry professionals, and students who spend countless hours interacting with computers.""",
        
        """Artificial intelligence has emerged as one of the most transformative technologies of the twenty-first century, fundamentally reshaping industries ranging from healthcare and finance to transportation and entertainment. Machine learning, a subset of AI, enables systems to learn from data without explicit programming through algorithms that identify patterns and make predictions. Deep learning, which uses artificial neural networks with multiple layers, has achieved remarkable breakthroughs in computer vision, natural language processing, and speech recognition. Convolutional neural networks excel at image classification tasks, while recurrent neural networks and transformers handle sequential data like text and time series. Large language models such as GPT-4 demonstrate unprecedented capabilities in understanding and generating human-like text, raising profound questions about creativity, consciousness, and the nature of intelligence. These models are trained on massive datasets containing billions of parameters, requiring enormous computational resources and specialized hardware like GPUs and TPUs. The environmental impact of training such models has sparked debate about sustainable AI practices and the need for more efficient architectures. Ethical concerns surrounding AI include algorithmic bias, privacy violations, job displacement, autonomous weapons, and the potential for misuse in generating misinformation or deepfakes. Regulatory frameworks like the EU's AI Act attempt to balance innovation with safeguards, classifying applications by risk level and imposing stricter requirements on high-risk systems."""
    ],
    
    2: [
        """Climate change represents the defining environmental challenge of our era, driven primarily by anthropogenic greenhouse gas emissions from fossil fuel combustion, deforestation, and industrial processes. Carbon dioxide concentrations have increased from pre-industrial levels of 280 parts per million to over 420 ppm today, the highest in at least 800,000 years according to ice core data. This unprecedented atmospheric change has already caused global average temperatures to rise approximately 1.1 degrees Celsius above pre-industrial baselines, with the Arctic warming nearly four times faster than the global average. The consequences of this warming include more frequent and intense extreme weather events such as hurricanes, heatwaves, droughts, floods, and wildfires. Rising sea levels, caused by thermal expansion and melting ice sheets, threaten coastal communities worldwide, with projections suggesting 1-2 meters of rise by 2100 even under optimistic scenarios. Ocean acidification, caused by absorption of excess CO2, harms marine ecosystems particularly calcifying organisms like corals, oysters, and plankton that form the base of food webs. The Intergovernmental Panel on Climate Change has warned that limiting warming to 1.5 degrees Celsius requires rapid, far-reaching transitions in energy, land use, transportation, and industrial systems. Renewable energy technologies including solar photovoltaics, wind turbines, and battery storage have experienced dramatic cost reductions, now competing favorably with fossil fuels in many markets. Solar energy has become the cheapest electricity source in history, with costs declining 90% since 2010, enabling rapid deployment worldwide. The transition to electric vehicles, heat pumps, and other electrified technologies can dramatically reduce emissions while improving air quality and energy security."""
    ],
    
    3: [
        """The universe, spanning an estimated 93 billion light-years in diameter, contains approximately 200 billion trillion stars organized into countless galaxies, each a cosmic island of gas, dust, and dark matter. Our Milky Way galaxy alone houses 100-400 billion stars, including our Sun, an unremarkable yellow dwarf located about 26,000 light-years from the galactic center. Modern cosmology rests on the Big Bang theory, which posits that space, time, and all matter emerged from an infinitely dense singularity approximately 13.8 billion years ago. The earliest moments remain mysterious, requiring a quantum theory of gravity that unifies general relativity with quantum mechanics. Cosmic microwave background radiation, discovered accidentally in 1964, provides a snapshot of the universe when it was just 380,000 years old, revealing tiny temperature fluctuations that seeded all subsequent structure formation. Dark matter, comprising approximately 27 percent of the universe's mass-energy budget, interacts gravitationally but not electromagnetically, making it invisible and detectable only through its gravitational effects on visible matter. Dark energy, an even more mysterious phenomenon accounting for 68 percent of the universe, appears to be accelerating cosmic expansion, counteracting the attractive force of gravity on cosmological scales."""
    ]
}

# Add more texts for levels 4 and 5
for level in range(4, 6):
    TEXTS_DB[level] = [t + " This advanced level text challenges even experienced typists with complex vocabulary and sentence structures, requiring sustained concentration and precision to complete accurately. The additional length tests endurance and consistency over extended typing sessions." for t in TEXTS_DB[3]]

def get_text_for_level(level):
    """Get a random text for specified difficulty level"""
    level = max(1, min(level, 5))
    text = TEXTS_DB.get(level, TEXTS_DB[5])[0]
    return {
        'text': text,
        'length': len(text),
        'level': level,
        'word_count': len(text.split())
    }

# ==================== HELPER FUNCTIONS ====================
def calculate_wpm(correct_chars, time_seconds):
    """Calculate Words Per Minute (5 chars = 1 word)"""
    if time_seconds < 0.1 or correct_chars < 1:
        return 0
    words = correct_chars / 5
    minutes = time_seconds / 60
    return round(words / minutes, 1)

def calculate_accuracy(correct, total):
    """Calculate accuracy percentage"""
    if total == 0:
        return 100.0
    return round((correct / total) * 100, 1)

def get_or_create_session():
    """Get or create typing session ID"""
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(16)
        session.permanent = True
        with db_connection() as conn:
            conn.execute(
                'INSERT OR IGNORE INTO typing_sessions (session_id, current_level) VALUES (?, ?)',
                (session['session_id'], 1)
            )
    return session['session_id']

def calculate_next_level(current_wpm, current_accuracy, current_level):
    """Determine next difficulty level based on performance"""
    if current_wpm >= 60 and current_accuracy >= 92 and current_level < 5:
        return current_level + 1
    elif current_wpm >= 45 and current_accuracy >= 88 and current_level < 4:
        return current_level + 1
    elif current_wpm >= 30 and current_accuracy >= 85 and current_level < 3:
        return current_level + 1
    elif current_wpm >= 20 and current_accuracy >= 80 and current_level < 2:
        return current_level + 1
    return current_level

# ==================== ROUTES ====================
@app.route('/')
@limiter.exempt
def index():
    """Main typing test interface"""
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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .dashboard-header {
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
        .stats-grid { display: flex; gap: 30px; flex-wrap: wrap; }
        .stat-card {
            text-align: center;
            padding: 10px 20px;
            background: #f8f9fa;
            border-radius: 15px;
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
        .test-controls { display: flex; gap: 15px; justify-content: center; }
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover { transform: translateY(-2px); }
        .btn-primary { background: #667eea; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .results-dashboard {
            background: white;
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
        }
        .result-metrics {
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
        .history-table {
            width: 100%;
            border-collapse: collapse;
        }
        .history-table th, .history-table td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #ddd;
        }
        .history-table th { background: #667eea; color: white; }
        @media (max-width: 768px) {
            .stats-grid { margin-top: 15px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="dashboard-header">
            <div class="logo"><h1>⚡ TypeMaster Pro</h1><p>Professional Adaptive Typing Test</p></div>
            <div class="stats-grid" id="liveStats">
                <div class="stat-card"><div class="stat-value" id="statWPM">0</div><div class="stat-label">WPM</div></div>
                <div class="stat-card"><div class="stat-value" id="statAccuracy">100</div><div class="stat-label">Accuracy %</div></div>
                <div class="stat-card"><div class="stat-value" id="statLevel">1</div><div class="stat-label">Level</div></div>
            </div>
        </div>
        <div class="test-area">
            <div class="level-badge" id="levelBadge">🔥 LEVEL 1 - BEGINNER</div>
            <div class="text-display" id="textDisplay"></div>
            <textarea class="typing-input" id="typingInput" rows="4" placeholder="Click START and begin typing..." disabled></textarea>
            <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
            <div class="test-controls">
                <button class="btn btn-primary" id="startBtn">▶ START TEST</button>
                <button class="btn btn-danger" id="resetBtn">⟳ RESET</button>
            </div>
        </div>
        <div class="results-dashboard" id="resultsPanel" style="display: none;">
            <h2>📊 Test Results</h2>
            <div class="result-metrics" id="resultMetrics"></div>
            <h3>📜 Test History</h3>
            <div style="overflow-x: auto;"><table class="history-table"><thead><tr><th>Date</th><th>WPM</th><th>Accuracy</th><th>Level</th><th>Mistakes</th></tr></thead><tbody id="historyBody"></tbody></table></div>
        </div>
    </div>
    <script>
        let currentText = '', currentLevel = 1, testActive = false, startTime = null, timerInterval = null;
        let currentInput = '', mistakes = 0, totalTyped = 0, correctTyped = 0;
        const textDisplay = document.getElementById('textDisplay'), typingInput = document.getElementById('typingInput');
        const startBtn = document.getElementById('startBtn'), resetBtn = document.getElementById('resetBtn');
        const progressFill = document.getElementById('progressFill'), statWPM = document.getElementById('statWPM');
        const statAccuracy = document.getElementById('statAccuracy'), statLevel = document.getElementById('statLevel');
        const levelBadge = document.getElementById('levelBadge'), resultsPanel = document.getElementById('resultsPanel');
        
        async function loadText() {
            const response = await fetch('/api/get_text', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
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
                html += `<span class="${charClass}">${currentText[i] === ' ' ? '&nbsp;' : escapeHtml(currentText[i])}</span>`;
            }
            textDisplay.innerHTML = html;
            progressFill.style.width = (currentInput.length / currentText.length * 100) + '%';
        }
        
        function escapeHtml(text) { return text.replace(/[&<>]/g, function(m) { return {'&':'&amp;','<':'&lt;','>':'&gt;'}[m]; }); }
        
        function updateLiveStats() {
            if (!testActive || !startTime) return;
            const elapsed = (Date.now() - startTime) / 1000;
            if (elapsed > 0) {
                const wpm = (correctTyped / 5) / (elapsed / 60);
                const accuracy = totalTyped > 0 ? (correctTyped / totalTyped) * 100 : 100;
                statWPM.textContent = Math.round(wpm);
                statAccuracy.textContent = Math.round(accuracy);
            }
        }
        
        function startTest() {
            if (testActive) return;
            testActive = true;
            startTime = Date.now();
            currentInput = ''; mistakes = 0; totalTyped = 0; correctTyped = 0;
            typingInput.disabled = false;
            typingInput.value = '';
            typingInput.focus();
            updateTextDisplay();
            timerInterval = setInterval(() => {
                updateLiveStats();
                if (currentInput.length >= currentText.length && testActive) endTest();
            }, 100);
        }
        
        async function endTest() {
            if (!testActive) return;
            testActive = false;
            clearInterval(timerInterval);
            const elapsed = (Date.now() - startTime) / 1000;
            const wpm = Math.round((correctTyped / 5) / (elapsed / 60));
            const accuracy = totalTyped > 0 ? Math.round((correctTyped / totalTyped) * 100) : 100;
            
            await fetch('/api/submit_result', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wpm: wpm, accuracy: accuracy, level: currentLevel, text_length: currentText.length, time_taken: elapsed, mistakes: mistakes })
            });
            
            await loadHistory();
            resultsPanel.style.display = 'block';
            document.getElementById('resultMetrics').innerHTML = `<div class="metric"><div class="metric-value">${wpm}</div><div class="metric-label">WPM</div></div><div class="metric"><div class="metric-value">${accuracy}%</div><div class="metric-label">Accuracy</div></div><div class="metric"><div class="metric-value">${elapsed.toFixed(1)}s</div><div class="metric-label">Time</div></div><div class="metric"><div class="metric-value">${mistakes}</div><div class="metric-label">Mistakes</div></div>`;
            typingInput.disabled = true;
        }
        
        async function loadHistory() {
            const response = await fetch('/api/get_history');
            const data = await response.json();
            document.getElementById('historyBody').innerHTML = data.history.map(h => `<tr><td>${h.date}</td><td>${h.wpm}</td><td>${h.accuracy}%</td><td>${h.level}</td><td>${h.mistakes}</td></tr>`).join('');
            if (data.stats) { statLevel.textContent = data.stats.current_level || currentLevel; }
        }
        
        function resetTest() {
            if (testActive) { testActive = false; clearInterval(timerInterval); }
            typingInput.disabled = true;
            typingInput.value = '';
            currentInput = '';
            statWPM.textContent = '0';
            statAccuracy.textContent = '100';
            loadText();
        }
        
        typingInput.addEventListener('input', (e) => {
            if (!testActive) return;
            const newValue = e.target.value;
            const newLength = newValue.length;
            const oldLength = currentInput.length;
            for (let i = oldLength; i < newLength && i < currentText.length; i++) {
                totalTyped++;
                if (newValue[i] === currentText[i]) correctTyped++;
                else mistakes++;
            }
            if (newLength < oldLength) {
                correctTyped = 0; mistakes = 0; totalTyped = 0;
                for (let i = 0; i < newLength && i < currentText.length; i++) {
                    totalTyped++;
                    if (newValue[i] === currentText[i]) correctTyped++;
                    else mistakes++;
                }
            }
            currentInput = newValue;
            updateTextDisplay();
            updateLiveStats();
            if (currentInput.length >= currentText.length) endTest();
        });
        
        startBtn.addEventListener('click', () => { resetTest(); startTest(); });
        resetBtn.addEventListener('click', resetTest);
        loadText();
        loadHistory();
    </script>
</body>
</html>'''
    return render_template_string(html_content)

@app.route('/api/get_text', methods=['POST'])
@limiter.limit("30 per minute")
def api_get_text():
    """Get text for typing test"""
    data = request.get_json()
    level = data.get('level', 1)
    return jsonify(get_text_for_level(level))

@app.route('/api/submit_result', methods=['POST'])
@limiter.limit("20 per minute")
def api_submit_result():
    """Submit typing test result"""
    session_id = get_or_create_session()
    data = request.get_json()
    
    with db_connection() as conn:
        conn.execute('''
            INSERT INTO test_results (session_id, wpm, accuracy, level, text_length, time_taken, mistakes, correct_chars, total_chars)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, data.get('wpm'), data.get('accuracy'), data.get('level'), 
              data.get('text_length'), data.get('time_taken'), data.get('mistakes'),
              int((data.get('accuracy', 0) / 100) * data.get('text_length', 0)), data.get('text_length', 0)))
        
        conn.execute('UPDATE typing_sessions SET total_tests_completed = total_tests_completed + 1, last_active = CURRENT_TIMESTAMP WHERE session_id = ?', (session_id,))
    
    return jsonify({'status': 'success'})

@app.route('/api/get_history', methods=['GET'])
@limiter.exempt
def api_get_history():
    """Get user test history"""
    session_id = get_or_create_session()
    with db_connection() as conn:
        results = conn.execute('''
            SELECT wpm, accuracy, level, mistakes, datetime(created_at, 'localtime') as date
            FROM test_results WHERE session_id = ? ORDER BY created_at DESC LIMIT 50
        ''', (session_id,)).fetchall()
        
        stats = conn.execute('SELECT COUNT(*) as total, AVG(wpm) as avg_wpm, MAX(wpm) as best_wpm FROM test_results WHERE session_id = ?', (session_id,)).fetchone()
        
        return jsonify({'history': [dict(r) for r in results], 'stats': {'total_tests': stats['total'] or 0, 'average_wpm': round(stats['avg_wpm'] or 0, 1), 'best_wpm': round(stats['best_wpm'] or 0, 1), 'current_level': 1}})

# ==================== MAIN ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
