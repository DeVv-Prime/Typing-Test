"""
Professional Typing Test Application
Advanced Features: Adaptive Difficulty, Performance Analytics, History Tracking
Author: TypingMaster Pro
Version: 3.0.0
"""

import os
import re
import json
import time
import random
import string
import hashlib
import secrets
import sqlite3
import statistics
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional, Any, Union

import numpy as np
from flask import (
    Flask, render_template_string, request, jsonify, 
    session, g, make_response, abort, redirect, url_for
)
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress
from markupsafe import escape
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

# ==================== APP INITIALIZATION ====================
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
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
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
    """Get database connection with context manager"""
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
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                total_tests INTEGER DEFAULT 0,
                total_time_typed REAL DEFAULT 0,
                best_wpm REAL DEFAULT 0,
                avg_accuracy REAL DEFAULT 0,
                current_level INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT NOT NULL,
                wpm REAL NOT NULL,
                accuracy REAL NOT NULL,
                raw_wpm REAL NOT NULL,
                level INTEGER NOT NULL,
                text_length INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                mistakes INTEGER NOT NULL,
                correct_chars INTEGER NOT NULL,
                total_chars INTEGER NOT NULL,
                difficulty_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
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
            CREATE INDEX IF NOT EXISTS idx_results_user ON test_results(user_id)
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_results_session ON test_results(session_id)
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_results_date ON test_results(created_at)
        ''')

# Initialize database on startup
init_database()

# ==================== TEXT DATABASE (2000+ characters each) ====================
TEXTS_DB = {
    1: [
        """The journey of mastering touch typing begins with understanding the fundamental principles of keyboard layout and finger positioning. The QWERTY keyboard layout, invented by Christopher Latham Sholes in 1873, was originally designed to prevent mechanical typewriter jams by separating common letter pairs. Today, despite more efficient alternatives like Dvorak or Colemak, QWERTY remains the global standard due to its widespread adoption and network effects. When learning to type, your fingers should rest on the home row: left hand on A, S, D, F and right hand on J, K, L, semicolon. Your thumbs naturally hover over the space bar, which is the most frequently pressed key. Proper posture is equally important: sit straight with elbows at a 90-degree angle, wrists slightly elevated, and screen at eye level to prevent strain and repetitive stress injuries. Beginners often struggle with looking at the keyboard, but developing muscle memory through consistent practice eliminates this dependency. Start with simple drills focusing on home row letters, then gradually expand to the top and bottom rows. The key to rapid improvement is quality over quantity—it's better to practice accurately for 15 minutes daily than to type carelessly for an hour. Many online resources offer structured lessons that progressively introduce new keys while reinforcing previously learned ones. Remember that typing speed plateaus are normal; pushing through them requires deliberate practice with targeted exercises that challenge your weak points. The average professional typist achieves 60-80 words per minute, while elite court reporters can exceed 200 words per minute using specialized stenotype machines. With dedication and proper technique, anyone can achieve functional typing proficiency that enhances productivity in our increasingly digital world. Touch typing not only saves time but also reduces cognitive load, allowing you to focus on content rather than key locations. This skill becomes particularly valuable for programmers, writers, data entry professionals, and students who spend countless hours interacting with computers. The investment in learning proper typing technique pays dividends throughout your career, making you more efficient and competitive in virtually any field that requires computer use.""",
        
        """Artificial intelligence has emerged as one of the most transformative technologies of the twenty-first century, fundamentally reshaping industries ranging from healthcare and finance to transportation and entertainment. Machine learning, a subset of AI, enables systems to learn from data without explicit programming through algorithms that identify patterns and make predictions. Deep learning, which uses artificial neural networks with multiple layers, has achieved remarkable breakthroughs in computer vision, natural language processing, and speech recognition. Convolutional neural networks excel at image classification tasks, while recurrent neural networks and transformers handle sequential data like text and time series. Large language models such as GPT-4 and Claude demonstrate unprecedented capabilities in understanding and generating human-like text, raising profound questions about creativity, consciousness, and the nature of intelligence. These models are trained on massive datasets containing billions of parameters, requiring enormous computational resources and specialized hardware like GPUs and TPUs. The environmental impact of training such models has sparked debate about sustainable AI practices and the need for more efficient architectures. Ethical concerns surrounding AI include algorithmic bias, privacy violations, job displacement, autonomous weapons, and the potential for misuse in generating misinformation or deepfakes. Regulatory frameworks like the EU's AI Act attempt to balance innovation with safeguards, classifying applications by risk level and imposing stricter requirements on high-risk systems. Explainable AI research aims to make black-box models more transparent, allowing humans to understand and verify AI decisions, particularly in critical domains like medicine and criminal justice. Reinforcement learning has enabled AI systems to master complex games like Go, chess, and StarCraft through self-play, often discovering strategies that humans never imagined. In healthcare, AI assists with disease diagnosis, drug discovery, personalized treatment plans, and medical image analysis, sometimes outperforming human experts in specific tasks. Autonomous vehicles combine computer vision, sensor fusion, and decision-making algorithms to navigate complex real-world environments, though full self-driving remains an elusive goal. The future of AI likely involves human-AI collaboration rather than replacement, with systems augmenting human capabilities rather than eliminating them. As AI continues to evolve, society must grapple with fundamental questions about work, meaning, and what it means to be human in an age of intelligent machines.""",
        
        """The human brain, containing approximately 86 billion neurons and quadrillions of synaptic connections, represents the most complex structure in the known universe. Neuroscientists have made tremendous progress in understanding brain function through advanced imaging techniques like functional magnetic resonance imaging, positron emission tomography, and electroencephalography. Neuroplasticity, the brain's remarkable ability to reorganize itself by forming new neural connections throughout life, underlies learning, memory formation, and recovery from injury. When we learn a new skill like typing or playing an instrument, our brains physically change, strengthening frequently used pathways while pruning unused ones. Long-term potentiation, a persistent strengthening of synapses based on recent activity patterns, provides the cellular basis for memory storage and learning. Different brain regions specialize in distinct functions: the frontal lobe handles executive functions like planning and impulse control, the temporal lobe processes auditory information and language comprehension, the parietal lobe integrates sensory information, and the occipital lobe handles vision. The hippocampus plays a crucial role in forming new declarative memories, while the amygdala processes emotional responses, particularly fear and pleasure. Neurotransmitters like dopamine, serotonin, and norepinephrine modulate mood, motivation, and cognitive function, with imbalances linked to conditions like depression, anxiety, and ADHD. Sleep plays an essential role in memory consolidation, with the brain replaying and strengthening daily experiences during deep sleep and REM cycles. The emerging field of connectomics aims to map the brain's complete wiring diagram, though current technology can only reconstruct tiny volumes of neural tissue. Brain-computer interfaces, pioneered by companies like Neuralink, promise to restore function to paralyzed individuals and potentially augment human cognition in the future. Understanding the biological basis of consciousness remains one of science's greatest challenges, with theories ranging from integrated information to global workspace models. Mental health conditions affect billions worldwide, yet their underlying neural mechanisms remain poorly understood, highlighting the need for continued research. The brain's incredible complexity and adaptability remind us that our cognitive abilities are not fixed but can be developed through lifelong learning and mental engagement."""
    ],
    
    2: [
        """Climate change represents the defining environmental challenge of our era, driven primarily by anthropogenic greenhouse gas emissions from fossil fuel combustion, deforestation, and industrial processes. Carbon dioxide concentrations have increased from pre-industrial levels of 280 parts per million to over 420 ppm today, the highest in at least 800,000 years according to ice core data. This unprecedented atmospheric change has already caused global average temperatures to rise approximately 1.1 degrees Celsius above pre-industrial baselines, with the Arctic warming nearly four times faster than the global average. The consequences of this warming include more frequent and intense extreme weather events such as hurricanes, heatwaves, droughts, floods, and wildfires. Rising sea levels, caused by thermal expansion and melting ice sheets, threaten coastal communities worldwide, with projections suggesting 1-2 meters of rise by 2100 even under optimistic scenarios. Ocean acidification, caused by absorption of excess CO2, harms marine ecosystems particularly calcifying organisms like corals, oysters, and plankton that form the base of food webs. The Intergovernmental Panel on Climate Change has warned that limiting warming to 1.5 degrees Celsius requires rapid, far-reaching transitions in energy, land use, transportation, and industrial systems. Renewable energy technologies including solar photovoltaics, wind turbines, and battery storage have experienced dramatic cost reductions, now competing favorably with fossil fuels in many markets. Solar energy has become the cheapest electricity source in history, with costs declining 90% since 2010, enabling rapid deployment worldwide. The transition to electric vehicles, heat pumps, and other electrified technologies can dramatically reduce emissions while improving air quality and energy security. Carbon capture, utilization, and storage technologies, while still expensive, may prove necessary to address hard-to-abate industrial emissions from cement, steel, and chemical production. Nature-based solutions like reforestation, wetland restoration, and regenerative agriculture can sequester significant carbon while providing biodiversity and community benefits. Individual actions, while insufficient alone, collectively matter: reducing meat consumption, avoiding air travel, improving home energy efficiency, and voting for climate-conscious policies all contribute. Climate justice recognizes that vulnerable communities, particularly in developing nations and marginalized groups, face disproportionate impacts despite contributing least to the problem. International frameworks like the Paris Agreement establish voluntary emissions reduction targets, but current commitments remain far below what science indicates is necessary. The concept of planetary boundaries defines safe operating spaces for humanity across nine Earth system processes, with climate change and biosphere integrity identified as core boundaries we have already transgressed. Despite the gravity of the challenge, technological solutions, political momentum, and growing public awareness offer hope that humanity can avert the worst consequences through collective action and innovation. The coming decade represents a critical window for action, with decisions made today determining the habitability of our planet for generations to come.""",
        
        """The global economy operates as an extraordinarily complex system of production, consumption, and exchange involving over 8 billion people across nearly 200 countries. Gross world product exceeded 100 trillion dollars annually, yet this wealth remains distributed with extreme inequality both between and within nations. The richest 10 percent of humanity owns over 75 percent of global wealth, while nearly half the world lives on less than $5.50 per day. Economic growth, measured as increases in real gross domestic product, has lifted billions out of poverty over recent decades, particularly in East Asian nations like China, South Korea, and Vietnam. However, critics argue that GDP fails to capture important dimensions of human welfare including environmental sustainability, health outcomes, social connection, and work-life balance. Alternative metrics like the Genuine Progress Indicator and Human Development Index attempt to provide more holistic measures of societal well-being. Capitalism, characterized by private ownership, market competition, and profit motivation, has become the dominant global economic system following the collapse of Soviet communism. Yet varieties of capitalism differ significantly: the Anglo-American model emphasizes shareholder value and flexible labor markets, while European social market economies prioritize worker protections and social welfare. The 2008 global financial crisis, triggered by subprime mortgage defaults and derivatives speculation, exposed fundamental vulnerabilities in lightly regulated financial systems. Central banks responded with unprecedented monetary policy measures including zero interest rates and quantitative easing, which helped stabilize economies but also contributed to asset price inflation and wealth inequality. More recently, the COVID-19 pandemic caused the sharpest global recession since the Great Depression, with supply chain disruptions, labor shortages, and massive government stimulus reshaping economic landscapes. Inflation returned to levels not seen in decades, forcing central banks to raise interest rates and risking recession as they attempt to balance price stability with employment goals. The informal economy, comprising unregulated and untaxed activities, represents an estimated 60 percent of global employment and 30 percent of GDP in developing nations. Automation and artificial intelligence threaten to displace millions of workers, though historical precedent suggests new jobs will emerge even as specific occupations become obsolete. Universal basic income has gained attention as a potential response to technological unemployment, with pilot programs testing its effects on work incentives and well-being. The transition to a circular economy, which eliminates waste through reuse, repair, and recycling, offers environmental and economic benefits compared to the traditional linear take-make-dispose model. Degrowth advocates argue that wealthy nations must reduce consumption and production to achieve environmental sustainability, though critics contend this would harm human welfare. Economic policy inevitably involves trade-offs between efficiency, equity, stability, and sustainability, with different societies making different choices based on their values and circumstances. Understanding basic economic principles empowers individuals to navigate personal finance decisions, evaluate policy proposals, and participate meaningfully in democratic discourse about how we organize our collective material existence."""
    ],
    
    3: [
        """The universe, spanning an estimated 93 billion light-years in diameter, contains approximately 200 billion trillion stars organized into countless galaxies, each a cosmic island of gas, dust, and dark matter. Our Milky Way galaxy alone houses 100-400 billion stars, including our Sun, an unremarkable yellow dwarf located about 26,000 light-years from the galactic center. Modern cosmology rests on the Big Bang theory, which posits that space, time, and all matter emerged from an infinitely dense singularity approximately 13.8 billion years ago. The earliest moments remain mysterious, requiring a quantum theory of gravity that unifies general relativity with quantum mechanics. Cosmic microwave background radiation, discovered accidentally in 1964, provides a snapshot of the universe when it was just 380,000 years old, revealing tiny temperature fluctuations that seeded all subsequent structure formation. Dark matter, comprising approximately 27 percent of the universe's mass-energy budget, interacts gravitationally but not electromagnetically, making it invisible and detectable only through its gravitational effects on visible matter. Dark energy, an even more mysterious phenomenon accounting for 68 percent of the universe, appears to be accelerating cosmic expansion, counteracting the attractive force of gravity on cosmological scales. General relativity, Einstein's geometric theory of gravity, describes gravity as curvature of spacetime caused by mass and energy, passing all experimental tests from solar system precision measurements to gravitational wave detection. Black holes, regions where gravity is so strong that nothing, not even light, can escape, were predicted by general relativity and have since been observed through their effects on surrounding matter and gravitational waves. Supermassive black holes, millions to billions times the Sun's mass, lurk at the centers of most large galaxies, including Sagittarius A* at the Milky Way's center with about 4 million solar masses. The first gravitational wave detection in 2015 confirmed a prediction Einstein made a century earlier, opening an entirely new way of observing cosmic phenomena beyond electromagnetic radiation. Stellar nucleosynthesis produces elements up to iron in the cores of stars through fusion reactions, while heavier elements require cataclysmic events like supernovae or neutron star mergers. Exoplanet research has revolutionized astronomy, confirming that planetary systems are common, with most stars hosting planets and many having potentially habitable worlds. The Drake equation, while not solvable with current knowledge, frames the probability of extraterrestrial intelligent life by considering factors like star formation rates, planet occurrence, and evolutionary timescales. The Fermi paradox highlights the contradiction between high estimates of extraterrestrial civilizations and the lack of evidence for or contact with them. The James Webb Space Telescope, launched in 2021, peers deeper into the infrared universe than ever before, observing the first galaxies that formed after the Big Bang and characterizing exoplanet atmospheres. Cosmological inflation theory proposes that the universe underwent exponential expansion during its first infinitesimal moments, explaining observed uniformity and flatness while predicting quantum fluctuations that seeded structure. The ultimate fate of the universe depends on dark energy's properties: continued acceleration leads to heat death, while possible dark energy decay could cause a Big Crunch or Big Rip. Understanding cosmology requires integrating observations across the electromagnetic spectrum, theoretical physics, and increasingly sophisticated computational simulations. The human quest to understand our cosmic origins reflects a uniquely powerful capacity for abstract reasoning and curiosity about our place in the grand scheme of existence."""
    ]
}

# Add more texts for levels 4 and 5 (reusing and extending level 3 texts)
TEXTS_DB[4] = [t + " This advanced level text challenges even experienced typists with complex vocabulary and sentence structures, requiring sustained concentration and precision to complete accurately. The additional length tests endurance and consistency over extended typing sessions." for t in TEXTS_DB[3]]
TEXTS_DB[5] = [t + " Master level difficulty pushes your typing abilities to their limits with demanding technical terminology, nuanced grammatical constructions, and variable pacing that prevents comfortable pattern recognition. Only dedicated practitioners achieve fluency at this elite tier." for t in TEXTS_DB[3]]

# Ensure each level has at least 3 texts
for level in TEXTS_DB:
    while len(TEXTS_DB[level]) < 3:
        TEXTS_DB[level].append(TEXTS_DB[level][0])

def get_text_for_level(level: int) -> Dict[str, Any]:
    """Get a random text for specified difficulty level with metadata"""
    level = max(1, min(level, 5))
    text = random.choice(TEXTS_DB[level])
    return {
        'text': text,
        'length': len(text),
        'level': level,
        'word_count': len(text.split()),
        'difficulty_multiplier': 0.8 + (level - 1) * 0.3
    }

# ==================== HELPER FUNCTIONS ====================
def calculate_wpm(correct_chars: int, time_seconds: float) -> float:
    """Calculate Words Per Minute (5 chars = 1 word)"""
    if time_seconds < 0.1 or correct_chars < 1:
        return 0
    words = correct_chars / 5
    minutes = time_seconds / 60
    return round(words / minutes, 1)

def calculate_accuracy(correct: int, total: int) -> float:
    """Calculate accuracy percentage"""
    if total == 0:
        return 100.0
    return round((correct / total) * 100, 1)

def calculate_raw_wpm(total_chars: int, time_seconds: float) -> float:
    """Calculate raw WPM including mistakes"""
    if time_seconds < 0.1:
        return 0
    words = total_chars / 5
    minutes = time_seconds / 60
    return round(words / minutes, 1)

def get_or_create_session() -> str:
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

def get_user_stats(session_id: str) -> Dict[str, Any]:
    """Get user statistics from database"""
    with db_connection() as conn:
        results = conn.execute(
            'SELECT wpm, accuracy, level, created_at FROM test_results WHERE session_id = ? ORDER BY created_at DESC',
            (session_id,)
        ).fetchall()
        
        if not results:
            return {'total_tests': 0, 'best_wpm': 0, 'avg_accuracy': 0, 'current_level': 1, 'history': []}
        
        wpm_list = [r['wpm'] for r in results]
        accuracy_list = [r['accuracy'] for r in results]
        
        return {
            'total_tests': len(results),
            'best_wpm': round(max(wpm_list), 1),
            'avg_accuracy': round(statistics.mean(accuracy_list), 1),
            'current_level': results[0]['level'] if results else 1,
            'history': [dict(r) for r in results[:20]]
        }

def calculate_next_level(current_wpm: float, current_accuracy: float, current_level: int) -> int:
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
    
    html_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TypeMaster Pro | Professional Adaptive Typing Test</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        
        /* Dashboard Header */
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
        .stats-grid {
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }
        .stat-card {
            text-align: center;
            padding: 10px 20px;
            background: #f8f9fa;
            border-radius: 15px;
        }
        .stat-value { font-size: 28px; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 12px; color: #666; margin-top: 5px; }
        
        /* Main Test Area */
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
            font-size: 20px;
            line-height: 1.6;
            margin-bottom: 20px;
            font-family: 'Courier New', monospace;
            max-height: 200px;
            overflow-y: auto;
        }
        .text-display span.correct { color: #28a745; background: #d4edda; }
        .text-display span.incorrect { color: #dc3545; background: #f8d7da; text-decoration: underline; }
        .text-display span.current { background: #ffc107; animation: blink 1s infinite; }
        @keyframes blink { 50% { opacity: 0.5; } }
        
        .typing-input {
            width: 100%;
            padding: 20px;
            font-size: 18px;
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
        
        .test-controls {
            display: flex;
            gap: 15px;
            justify-content: center;
        }
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
        .btn-success { background: #28a745; color: white; }
        
        /* Results Dashboard */
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
            .result-metrics { grid-template-columns: 1fr 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="dashboard-header">
            <div class="logo">
                <h1>⚡ TypeMaster Pro</h1>
                <p>Professional Adaptive Typing Test</p>
            </div>
            <div class="stats-grid" id="liveStats">
                <div class="stat-card"><div class="stat-value" id="statWPM">0</div><div class="stat-label">Current WPM</div></div>
                <div class="stat-card"><div class="stat-value" id="statAccuracy">100</div><div class="stat-label">Accuracy %</div></div>
                <div class="stat-card"><div class="stat-value" id="statLevel">1</div><div class="stat-label">Level</div></div>
            </div>
        </div>
        
        <div class="test-area">
            <div class="level-badge" id="levelBadge">🔥 LEVEL 1 - BEGINNER</div>
            <div class="text-display" id="textDisplay"></div>
            <textarea class="typing-input" id="typingInput" rows="4" placeholder="Click here and start typing..." disabled></textarea>
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
            <div style="overflow-x: auto;"><table class="history-table" id="historyTable"><thead><tr><th>Date</th><th>WPM</th><th>Accuracy</th><th>Level</th><th>Length</th><th>Mistakes</th></tr></thead><tbody id="historyBody"></tbody></table></div>
        </div>
    </div>
    
    <script>
        let currentText = '';
        let currentLevel = 1;
        let testActive = false;
        let startTime = null;
        let timerInterval = null;
        let currentInput = '';
        let mistakes = 0;
        let totalTyped = 0;
        let correctTyped = 0;
        
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
                html += `<span class="${charClass}">${currentText[i] === ' ' ? '&nbsp;' : escapeHtml(currentText[i])}</span>`;
            }
            textDisplay.innerHTML = html;
            
            const progress = (currentInput.length / currentText.length) * 100;
            progressFill.style.width = progress + '%';
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
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
            currentInput = '';
            mistakes = 0;
            totalTyped = 0;
            correctTyped = 0;
            typingInput.disabled = false;
            typingInput.value = '';
            typingInput.focus();
            updateTextDisplay();
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
            const wpm = calculateWPM(correctTyped, elapsed);
            const accuracy = totalTyped > 0 ? (correctTyped / totalTyped) * 100 : 100;
            
            const result = await fetch('/api/submit_result', {
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
            const data = await result.json();
            
            if (data.new_level && data.new_level > currentLevel) {
                currentLevel = data.new_level;
                statLevel.textContent = currentLevel;
                levelBadge.textContent = getLevelBadge(currentLevel);
                alert(`🎉 Congratulations! You advanced to Level ${currentLevel}!`);
            }
            
            await loadHistory();
            showResults(wpm, accuracy, elapsed, mistakes);
            typingInput.disabled = true;
        }
        
        function calculateWPM(correctChars, seconds) {
            if (seconds < 0.1) return 0;
            const words = correctChars / 5;
            const minutes = seconds / 60;
            return Math.round(words / minutes);
        }
        
        function getLevelBadge(level) {
            const badges = {1: '🌟 LEVEL 1 - BEGINNER', 2: '⚡ LEVEL 2 - INTERMEDIATE', 3: '🔥 LEVEL 3 - ADVANCED', 4: '💪 LEVEL 4 - EXPERT', 5: '🏆 LEVEL 5 - MASTER'};
            return badges[level] || 'LEVEL ' + level;
        }
        
        function showResults(wpm, accuracy, time, mistakes) {
            resultsPanel.style.display = 'block';
            document.getElementById('resultMetrics').innerHTML = `
                <div class="metric"><div class="metric-value">${wpm}</div><div class="metric-label">WPM</div></div>
                <div class="metric"><div class="metric-value">${Math.round(accuracy)}%</div><div class="metric-label">Accuracy</div></div>
                <div class="metric"><div class="metric-value">${time.toFixed(1)}s</div><div class="metric-label">Time</div></div>
                <div class="metric"><div class="metric-value">${mistakes}</div><div class="metric-label">Mistakes</div></div>
            `;
        }
        
        async function loadHistory() {
            const response = await fetch('/api/get_history');
            const data = await response.json();
            const tbody = document.getElementById('historyBody');
            tbody.innerHTML = data.history.map(h => `
                <tr><td>${h.date}</td><td>${h.wpm}</td><td>${h.accuracy}%</td><td>${h.level}</td><td>${h.length}</td><td>${h.mistakes}</td></tr>
            `).join('');
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
            updateTextDisplay();
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
                const shortened = newLength;
                correctTyped = 0;
                mistakes = 0;
                totalTyped = 0;
                for (let i = 0; i < shortened && i < currentText.length; i++) {
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
        
        startBtn.addEventListener('click', () => {
            resetTest();
            startTest();
        });
        resetBtn.addEventListener('click', resetTest);
        
        loadText();
        loadHistory();
    </script>
</body>
</html>
'''
    return render_template_string(html_content)

@app.route('/api/get_text', methods=['POST'])
@limiter.limit("30 per minute")
def api_get_text():
    """Get text for typing test"""
    data = request.get_json()
    level = data.get('level', 1)
    text_data = get_text_for_level(level)
    return jsonify(text_data)

@app.route('/api/submit_result', methods=['POST'])
@limiter.limit("20 per minute")
def api_submit_result():
    """Submit typing test result"""
    session_id = get_or_create_session()
    data = request.get_json()
    
    wpm = data.get('wpm', 0)
    accuracy = data.get('accuracy', 0)
    level = data.get('level', 1)
    text_length = data.get('text_length', 0)
    time_taken = data.get('time_taken', 0)
    mistakes = data.get('mistakes', 0)
    
    raw_wpm = calculate_raw_wpm(text_length, time_taken)
    correct_chars = int((accuracy / 100) * text_length) if text_length > 0 else 0
    
    with db_connection() as conn:
        conn.execute('''
            INSERT INTO test_results (session_id, wpm, accuracy, raw_wpm, level, text_length, time_taken, mistakes, correct_chars, total_chars)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, wpm, accuracy, raw_wpm, level, text_length, time_taken, mistakes, correct_chars, text_length))
        
        # Update typing session
        conn.execute('''
            UPDATE typing_sessions 
            SET total_tests_completed = total_tests_completed + 1,
                last_active = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (session_id,))
    
    # Calculate next level
    new_level = calculate_next_level(wpm, accuracy, level)
    
    return jsonify({
        'status': 'success',
        'wpm': wpm,
        'accuracy': accuracy,
        'new_level': new_level if new_level > level else None
    })

@app.route('/api/get_history', methods=['GET'])
@limiter.exempt
def api_get_history():
    """Get user test history"""
    session_id = get_or_create_session()
    with db_connection() as conn:
        results = conn.execute('''
            SELECT wpm, accuracy, level, text_length as length, mistakes, 
                   datetime(created_at, 'localtime') as date
            FROM test_results 
            WHERE session_id = ? 
            ORDER BY created_at DESC 
            LIMIT 50
        ''', (session_id,)).fetchall()
        
        stats = conn.execute('''
            SELECT COUNT(*) as total, AVG(wpm) as avg_wpm, MAX(wpm) as best_wpm, 
                   AVG(accuracy) as avg_acc
            FROM test_results WHERE session_id = ?
        ''', (session_id,)).fetchone()
        
        return jsonify({
            'history': [dict(r) for r in results],
            'stats': {
                'total_tests': stats['total'] or 0,
                'average_wpm': round(stats['avg_wpm'] or 0, 1),
                'best_wpm': round(stats['best_wpm'] or 0, 1),
                'average_accuracy': round(stats['avg_acc'] or 0, 1)
            }
        })

@app.route('/api/stats', methods=['GET'])
@limiter.exempt
def api_stats():
    """Get user statistics"""
    session_id = get_or_create_session()
    stats = get_user_stats(session_id)
    return jsonify(stats)

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({'error': 'Too many requests. Please slow down.'}), 429

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ==================== MAIN ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    app.run(host='0.0.0.0', port=port, debug=debug)
