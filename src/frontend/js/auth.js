// ==================== AUTH HANDLERS ====================

function initAuthHandlers() {
    // Login Button
    document.getElementById('login-btn').addEventListener('click', handleLogin);
    
    // Register Button
    document.getElementById('register-btn').addEventListener('click', handleRegister);
    
    // Check Username Button
    document.getElementById('check-username-btn').addEventListener('click', checkUsernameAvailability);
}

// ==================== LOGIN ====================

async function handleLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    
    // Validation
    if (!username) {
        showAlert('Bitte gib einen Benutzernamen ein.');
        return;
    }
    
    if (!password) {
        showAlert('Bitte gib ein Passwort ein.');
        return;
    }
    
    const loginBtn = document.getElementById('login-btn');
    loginBtn.disabled = true;
    loginBtn.textContent = 'Anmeldung läuft...';
    showLoading(true);
    
    try {
        const result = await apiRequest('/wahlplakatgame/api/auth/login', 'POST', {
            nickname: username,
            password: password
        });
        
        if (result.success) {
            // Save session
            saveSession(result.token, {
                user_id: result.user_id,
                nickname: result.nickname,
                points: result.points
            });
            
            // Show success message
            const lastLogin = result.last_login_time || 'Unbekannt';
            const lastIp = result.last_login_ip || 'Unbekannt';
            
            showAlert(
                `Willkommen zurück, ${result.nickname}!\n\n` +
                `Punkte: ${result.points}\n` +
                `Letzte Anmeldung: ${lastLogin}\n` +
                `IP: ${lastIp}`
            );
            
            // Load game
            await loadGamePage();
        } else {
            showAlert(`Anmeldung fehlgeschlagen!\n\n${result.message}`);
        }
    } catch (error) {
        console.error('Login error:', error);
        showAlert('Fehler beim Anmelden. Bitte versuche es erneut.');
    } finally {
        loginBtn.disabled = false;
        loginBtn.textContent = 'Anmelden';
        showLoading(false);
    }
}

// ==================== REGISTER ====================

async function handleRegister() {
    const username = document.getElementById('register-username').value.trim();
    const password = document.getElementById('register-password').value;
    const passwordRepeat = document.getElementById('register-password-repeat').value;
    
    // Validation
    if (!username) {
        showAlert('Bitte gib einen Benutzernamen ein.');
        return;
    }
    
    if (username.length > 18) {
        showAlert('Benutzername darf maximal 18 Zeichen lang sein.');
        return;
    }
    
    if (!password) {
        showAlert('Bitte gib ein Passwort ein.');
        return;
    }
    
    if (password.length < 6) {
        showAlert('Passwort muss mindestens 6 Zeichen lang sein.');
        return;
    }
    
    if (password !== passwordRepeat) {
        showAlert('Die Passwörter stimmen nicht überein.');
        return;
    }
    
    const registerBtn = document.getElementById('register-btn');
    registerBtn.disabled = true;
    registerBtn.textContent = 'Erstelle Konto...';
    showLoading(true);
    
    try {
        const result = await apiRequest('/wahlplakatgame/api/auth/register', 'POST', {
            nickname: username,
            password: password
        });
        
        if (result.success) {
            showAlert(
                `Konto erfolgreich erstellt!\n\n` +
                `Du kannst dich jetzt mit deinem Benutzernamen "${username}" anmelden.\n\n` +
                `Viel Spaß beim Spielen!`
            );
            
            // Clear form
            document.getElementById('register-username').value = '';
            document.getElementById('register-password').value = '';
            document.getElementById('register-password-repeat').value = '';
            document.getElementById('username-status').textContent = '';
            
            // Switch to login tab
            document.querySelector('[data-tab="login"]').click();
            
            // Pre-fill username
            document.getElementById('login-username').value = username;
        } else {
            showAlert(`Registrierung fehlgeschlagen!\n\n${result.message}`);
        }
    } catch (error) {
        console.error('Register error:', error);
        showAlert('Fehler bei der Registrierung. Bitte versuche es erneut.');
    } finally {
        registerBtn.disabled = false;
        registerBtn.textContent = 'Konto erstellen';
        showLoading(false);
    }
}

// ==================== CHECK USERNAME ====================

async function checkUsernameAvailability() {
    const username = document.getElementById('register-username').value.trim();
    const statusEl = document.getElementById('username-status');
    
    if (!username) {
        statusEl.textContent = 'Bitte gib zuerst einen Benutzernamen ein.';
        statusEl.className = 'status-text error';
        return;
    }
    
    if (username.length > 18) {
        statusEl.textContent = '❌ Benutzername zu lang (max. 18 Zeichen)';
        statusEl.className = 'status-text error';
        return;
    }
    
    const checkBtn = document.getElementById('check-username-btn');
    checkBtn.disabled = true;
    checkBtn.textContent = 'Prüfe...';
    
    try {
        const result = await apiRequest('/wahlplakatgame/api/auth/check-username', 'POST', {
            nickname: username
        });
        
        if (result.available) {
            statusEl.textContent = '✓ Benutzername verfügbar!';
            statusEl.className = 'status-text success';
        } else {
            statusEl.textContent = '❌ Benutzername bereits vergeben';
            statusEl.className = 'status-text error';
        }
    } catch (error) {
        console.error('Check username error:', error);
        statusEl.textContent = '❌ Fehler beim Prüfen';
        statusEl.className = 'status-text error';
    } finally {
        checkBtn.disabled = false;
        checkBtn.textContent = 'Prüfen';
    }
}
