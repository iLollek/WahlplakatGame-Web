// ==================== GLOBAL STATE ====================

const AppState = {
    currentPage: 'auth',
    sessionToken: null,
    userInfo: null,
    socket: null,
    sounds: {},
    parteien: []
};

// ==================== UTILITY FUNCTIONS ====================

function showPage(pageName) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(`${pageName}-page`).classList.add('active');
    AppState.currentPage = pageName;
}

function showLoading(show = true) {
    const overlay = document.getElementById('loading-overlay');
    if (show) {
        overlay.classList.add('active');
    } else {
        overlay.classList.remove('active');
    }
}

function showAlert(message, type = 'info') {
    // Einfaches Alert - könnte durch Toast-Notifications ersetzt werden
    alert(message);
}

function showConfirm(message) {
    return confirm(message);
}

function saveSession(token, userInfo) {
    localStorage.setItem('session_token', token);
    localStorage.setItem('user_info', JSON.stringify(userInfo));
    AppState.sessionToken = token;
    AppState.userInfo = userInfo;
}

function loadSession() {
    const token = localStorage.getItem('session_token');
    const userInfo = localStorage.getItem('user_info');
    
    if (token && userInfo) {
        AppState.sessionToken = token;
        AppState.userInfo = JSON.parse(userInfo);
        return true;
    }
    return false;
}

function clearSession() {
    localStorage.removeItem('session_token');
    localStorage.removeItem('user_info');
    AppState.sessionToken = null;
    AppState.userInfo = null;
}

// ==================== API HELPER ====================

async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(endpoint, options);
        return await response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

// ==================== SOUND SYSTEM ====================

function initSounds() {
    const soundFiles = {
        correct: '/wahlplakatgame/assets/sounds/correct_answer.mp3',
        incorrect: '/wahlplakatgame/assets/sounds/incorrect_answer.mp3',
        join: '/wahlplakatgame/assets/sounds/player_join.mp3',
        leave: '/wahlplakatgame/assets/sounds/player_leave.mp3',
        lock: '/wahlplakatgame/assets/sounds/lock_answer.mp3'
    };
    
    for (const [name, path] of Object.entries(soundFiles)) {
        const audio = new Audio(path);
        audio.preload = 'auto';
        AppState.sounds[name] = audio;
    }
}

function playSound(soundName) {
    if (AppState.sounds[soundName]) {
        // Clone audio to allow multiple plays
        const sound = AppState.sounds[soundName].cloneNode();
        sound.volume = 0.5;
        sound.play().catch(e => console.warn('Sound play failed:', e));
    }
}

// ==================== TAB SYSTEM ====================

function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // Update buttons
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Update content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${tabName}-tab`).classList.add('active');
        });
    });
}

// ==================== ENTER KEY HANDLER ====================

function setupEnterKeyHandlers() {
    // Login form
    const loginUsername = document.getElementById('login-username');
    const loginPassword = document.getElementById('login-password');
    
    [loginUsername, loginPassword].forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('login-btn').click();
            }
        });
    });
    
    // Register form
    const registerUsername = document.getElementById('register-username');
    const registerPassword = document.getElementById('register-password');
    const registerPasswordRepeat = document.getElementById('register-password-repeat');
    
    [registerUsername, registerPassword, registerPasswordRepeat].forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('register-btn').click();
            }
        });
    });
}

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎮 WahlplakatGame lädt...');
    
    // Setup UI
    setupTabs();
    setupEnterKeyHandlers();
    
    // Init sounds
    initSounds();
    
    // Check for existing session
    if (loadSession()) {
        console.log('📱 Session gefunden, validiere...');
        validateAndRestore();
    } else {
        console.log('📱 Keine Session, zeige Login');
        showPage('auth');
    }
    
    // Init Auth handlers
    if (typeof initAuthHandlers === 'function') {
        initAuthHandlers();
    }
    
    // Init Game handlers
    if (typeof initGameHandlers === 'function') {
        initGameHandlers();
    }
});

async function validateAndRestore() {
    showLoading(true);
    
    try {
        const result = await apiRequest('/wahlplakatgame/api/auth/validate', 'POST', {
            token: AppState.sessionToken
        });
        
        if (result.valid) {
            console.log('✅ Session gültig');
            AppState.userInfo = {
                user_id: result.user_id,
                nickname: result.nickname,
                points: result.points
            };
            
            // Load game
            await loadGamePage();
        } else {
            console.log('❌ Session ungültig');
            clearSession();
            showPage('auth');
        }
    } catch (error) {
        console.error('Fehler bei Session-Validierung:', error);
        clearSession();
        showPage('auth');
    } finally {
        showLoading(false);
    }
}

// ==================== WINDOW UNLOAD ====================

window.addEventListener('beforeunload', () => {
    if (AppState.socket && AppState.socket.connected) {
        AppState.socket.emit('leave_game', {
            token: AppState.sessionToken,
            reason: 'request'
        });
    }
});
