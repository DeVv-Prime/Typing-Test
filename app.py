"""
Professional Typing Test Application
Fixed for Python 3.11 compatibility
"""

import os
import secrets
import sqlite3
import statistics
from datetime import datetime, timedelta
from contextlib import contextmanager
from flask import Flask, render_template_string, request, jsonify, session

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['JSON_SORT_KEYS'] = False

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
                level INTEGER NOT NULL,
                text_length INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                mistakes INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_results_session ON test_results(session_id)
        ''')

# Initialize database
init_database()

# ==================== TEXT DATABASE (2000+ characters) ====================
TEXTS = {
    1: [
        """The journey of mastering touch typing begins with understanding the fundamental principles of keyboard layout and finger positioning. The QWERTY keyboard layout, invented by Christopher Latham Sholes in 1873, was originally designed to prevent mechanical typewriter jams by separating common letter pairs. Today, despite more efficient alternatives like Dvorak or Colemak, QWERTY remains the global standard due to its widespread adoption and network effects. When learning to type, your fingers should rest on the home row: left hand on A, S, D, F and right hand on J, K, L, semicolon. Your thumbs naturally hover over the space bar, which is the most frequently pressed key. Proper posture is equally important: sit straight with elbows at a 90-degree angle, wrists slightly elevated, and screen at eye level to prevent strain and repetitive stress injuries. Beginners often struggle with looking at the keyboard, but developing muscle memory through consistent practice eliminates this dependency. Start with simple drills focusing on home row letters, then gradually expand to the top and bottom rows. The key to rapid improvement is quality over quantity—it's better to practice accurately for 15 minutes daily than to type carelessly for an hour. The average professional typist achieves 60-80 words per minute, while elite court reporters can exceed 200 words per minute. With dedication and proper technique, anyone can achieve functional typing proficiency that enhances productivity in our increasingly digital world.""",
        
        """Artificial intelligence has emerged as one of the most transformative technologies of the twenty-first century, fundamentally reshaping industries ranging from healthcare and finance to transportation and entertainment. Machine learning, a subset of AI, enables systems to learn from data without explicit programming through algorithms that identify patterns and make predictions. Deep learning, which uses artificial neural networks with multiple layers, has achieved remarkable breakthroughs in computer vision, natural language processing, and speech recognition. Convolutional neural networks excel at image classification tasks, while recurrent neural networks and transformers handle sequential data like text and time series. Large language models demonstrate unprecedented capabilities in understanding and generating human-like text, raising profound questions about creativity and consciousness. These models are trained on massive datasets containing billions of parameters, requiring enormous computational resources. The environmental impact of training such models has sparked debate about sustainable AI practices. Ethical concerns surrounding AI include algorithmic bias, privacy violations, and job displacement."""
    ],
    2: [
        """Climate change represents the defining environmental challenge of our era, driven primarily by anthropogenic greenhouse gas emissions from fossil fuel combustion, deforestation, and industrial processes. Carbon dioxide concentrations have increased from pre-industrial levels of 280 parts per million to over 420 ppm today, the highest in at least 800,000 years according to ice core data. This unprecedented atmospheric change has already caused global average temperatures to rise approximately 1.1 degrees Celsius above pre-industrial baselines, with the Arctic warming nearly four times faster than the global average. The consequences include more frequent and intense extreme weather events such as hurricanes, heatwaves, droughts, floods, and wildfires. Rising sea levels threaten coastal communities worldwide, with projections suggesting 1-2 meters of rise by 2100. Ocean acidification harms marine ecosystems, particularly calcifying organisms like corals and oysters. Renewable energy technologies including solar photovoltaics, wind turbines, and battery storage have experienced dramatic cost reductions, now competing favorably with fossil fuels. The transition to electric vehicles, heat pumps, and other electrified technologies can dramatically reduce emissions while improving air quality."""
    ],
    3: [
        """The universe spans an estimated 93 billion light-years in diameter and contains approximately 200 billion trillion stars organized into countless galaxies. Our Milky Way galaxy alone houses 100-400 billion stars, including our Sun, an unremarkable yellow dwarf located about 26,000 light-years from the galactic center. Modern cosmology rests on the Big Bang theory, which posits that space, time, and all matter emerged from an infinitely dense singularity approximately 13.8 billion years ago. Cosmic microwave background radiation provides a snapshot of the universe when it was just 380,000 years old, revealing tiny temperature fluctuations that seeded all subsequent structure formation. Dark matter comprises approximately 27 percent of the universe's mass-energy budget and interacts gravitationally but not electromagnetically. Dark energy, accounting for 68 percent of the universe, appears to be accelerating cosmic expansion. Black holes are regions where gravity is so strong that nothing, not even light, can escape. The first gravitational wave detection in 2015 confirmed a prediction Einstein made a century ago."""
    ]
}

# Add level 4 and 5 texts
for level in range(4, 6):
    TEXTS[level] = [t + " This advanced level challenges experienced typists with complex vocabulary and sentence structures, requiring sustained concentration and precision. The additional length tests endurance and consistency over extended typing sessions." for t in TEXTS[3]]

def get_text_for_level(level):
    """Get a random text for specified difficulty level"""
    level = max(1, min(level, 5))
    text = TEXTS.get(level, TEXTS[5])[0]
    return {
        'text': text,
        'length': len(text),
        'level': level
    }

# ==================== HELPER FUNCTIONS ====================
def get_or_create_session():
    """Get or create typing session ID"""
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(16)
        session.permanent = True
    return session['session_id']

# ==================== ROUTES ====================
@app.route('/')
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
        .stats {
            display: flex;
            gap: 20px;
        }
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
        .controls { display: flex; gap: 15px; justify-content: center; }
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
            .stat-card { min-width: 80px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo"><h1>⚡ TypeMaster Pro</h1><p>Professional Adaptive Typing Test</p></div>
            <div class="stats">
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
            <div class="controls">
                <button class="btn btn-primary" id="startBtn">▶ START TEST</button>
                <button class="btn btn-danger" id="resetBtn">⟳ RESET</button>
            </div>
        </div>
        <div class="results" id="resultsPanel" style="display: none;">
            <h2>📊 Test Results</h2>
            <div class="metrics" id="resultMetrics"></div>
            <h3>📜 Test History</h3>
            <div style="overflow-x: auto;"><table><thead><tr><th>Date</th><th>WPM</th><th>Accuracy</th><th>Level</th><th>Mistakes</th></tr></thead><tbody id="historyBody"></tbody></table></div>
        </div>
    </div>
    <script>
        let currentText = '', currentLevel = 1, testActive = false, startTime = null;
        let currentInput = '', mistakes = 0, totalTyped = 0, correctTyped = 0;
        let timerInterval = null;
        
        const textDisplay = document.getElementById('textDisplay');
        const typingInput = document.getElementById('typingInput');
        const startBtn = document.getElementById('startBtn');
        const resetBtn = document.getElementById('resetBtn');
        const progressFill = document.getElementById('progressFill');
        const statWPM = document.getElementById('statWPM');
        const statAccuracy = document.getElementById('statAccuracy');
        const statLevel = document.getElementById('statLevel');
        const levelBadge = document.getElementById('levelBadge');
        const resultsPanel = document.getElementById('resultsPanel');
        
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
            textDisplay.innerHTML = html;
            let progress = (currentInput.length / currentText.length) * 100;
            progressFill.style.width = progress + '%';
        }
        
        function updateLiveStats() {
            if (!testActive || !startTime) return;
            const elapsed = (Date.now() - startTime) / 1000;
            if (elapsed > 0 && totalTyped > 0) {
                const wpm = Math.round((correctTyped / 5) / (elapsed / 60));
                const accuracy = Math.round((correctTyped / totalTyped) * 100);
                statWPM.textContent = wpm;
                statAccuracy.textContent = accuracy;
            }
        }
        
        function startTest() {
            if (testActive) return;
            testActive = true;
            startTime = Date.now();
            currentInput = '';
            mistakes = 0;
            totalTyped = 0;
            correctTyped = 0;
            typingInput.disabled = false;
            typingInput.value = '';
            typingInput.focus();
            updateTextDisplay();
            if (timerInterval) clearInterval(timerInterval);
            timerInterval = setInterval(() => {
                updateLiveStats();
                if (currentInput.length >= currentText.length && testActive) {
                    endTest();
                }
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
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    wpm: wpm,
                    accuracy: accuracy,
                    level: currentLevel,
                    text_length: currentText.length,
                    time_taken: elapsed,
                    mistakes: mistakes
                })
            });
            
            await loadHistory();
            resultsPanel.style.display = 'block';
            document.getElementById('resultMetrics').innerHTML = `
                <div class="metric"><div class="metric-value">${wpm}</div><div class="metric-label">WPM</div></div>
                <div class="metric"><div class="metric-value">${accuracy}%</div><div class="metric-label">Accuracy</div></div>
                <div class="metric"><div class="metric-value">${elapsed.toFixed(1)}s</div><div class="metric-label">Time</div></div>
                <div class="metric"><div class="metric-value">${mistakes}</div><div class="metric-label">Mistakes</div></div>
            `;
            typingInput.disabled = true;
        }
        
        async function loadHistory() {
            const response = await fetch('/api/get_history');
            const data = await response.json();
            const tbody = document.getElementById('historyBody');
            if (data.history && data.history.length > 0) {
                tbody.innerHTML = data.history.map(h => `
                    <tr><td>${h.date}</td><td>${h.wpm}</td><td>${h.accuracy}%</td><td>${h.level}</td><td>${h.mistakes}</td></tr>
                `).join('');
            }
        }
        
        function resetTest() {
            if (testActive) {
                testActive = false;
                clearInterval(timerInterval);
            }
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
            
            if (currentInput.length >= currentText.length) {
                endTest();
            }
        });
        
        startBtn.addEventListener('click', () => { resetTest(); startTest(); });
        resetBtn.addEventListener('click', resetTest);
        
        loadText();
        loadHistory();
        
        const levelNames = {1:'BEGINNER',2:'INTERMEDIATE',3:'ADVANCED',4:'EXPERT',5:'MASTER'};
        setInterval(async () => {
            const resp = await fetch('/api/get_level');
            const data = await resp.json();
            if (data.level !== currentLevel) {
                currentLevel = data.level;
                statLevel.textContent = currentLevel;
                levelBadge.textContent = `🔥 LEVEL ${currentLevel} - ${levelNames[currentLevel] || 'PRO'}`;
                loadText();
            }
        }, 3000);
    </script>
</body>
</html>'''
    return render_template_string(html_content)

@app.route('/api/get_text', methods=['POST'])
def api_get_text():
    """Get text for typing test"""
    data = request.get_json()
    level = data.get('level', 1)
    return jsonify(get_text_for_level(level))

@app.route('/api/submit_result', methods=['POST'])
def api_submit_result():
    """Submit typing test result"""
    session_id = get_or_create_session()
    data = request.get_json()
    
    with db_connection() as conn:
        conn.execute('''
            INSERT INTO test_results (session_id, wpm, accuracy, level, text_length, time_taken, mistakes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, data.get('wpm'), data.get('accuracy'), data.get('level'), 
              data.get('text_length'), data.get('time_taken'), data.get('mistakes')))
    
    return jsonify({'status': 'success'})

@app.route('/api/get_history', methods=['GET'])
def api_get_history():
    """Get user test history"""
    session_id = get_or_create_session()
    with db_connection() as conn:
        results = conn.execute('''
            SELECT wpm, accuracy, level, mistakes, 
                   datetime(created_at, 'localtime') as date
            FROM test_results 
            WHERE session_id = ? 
            ORDER BY created_at DESC 
            LIMIT 50
        ''', (session_id,)).fetchall()
        
        return jsonify({'history': [dict(r) for r in results]})

@app.route('/api/get_level', methods=['GET'])
def api_get_level():
    """Get current user level"""
    session_id = get_or_create_session()
    with db_connection() as conn:
        results = conn.execute('''
            SELECT wpm, accuracy, level FROM test_results 
            WHERE session_id = ? ORDER BY created_at DESC LIMIT 5
        ''', (session_id,)).fetchall()
        
        current_level = 1
        if results:
            avg_wpm = statistics.mean([r['wpm'] for r in results])
            avg_acc = statistics.mean([r['accuracy'] for r in results])
            
            if avg_wpm >= 60 and avg_acc >= 92:
                current_level = 5
            elif avg_wpm >= 45 and avg_acc >= 88:
                current_level = 4
            elif avg_wpm >= 30 and avg_acc >= 85:
                current_level = 3
            elif avg_wpm >= 20 and avg_acc >= 80:
                current_level = 2
        
        return jsonify({'level': current_level})

# ==================== MAIN ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
