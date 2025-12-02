// ==================== GAME STATE ====================

const GameState = {
    hasAnswered: false,
    currentQuelle: null,
    canAnswer: true
};

// ==================== GAME INITIALIZATION ====================

function initGameHandlers() {
    // Answer Button
    document.getElementById('answer-btn').addEventListener('click', submitAnswer);
    
    // Source Button
    document.getElementById('source-btn').addEventListener('click', showSource);
    
    // Leave Button
    document.getElementById('leave-btn').addEventListener('click', leaveGame);
}

async function loadGamePage() {
    console.log('🎮 Lade Spiel-Seite...');
    showLoading(true);
    
    try {
        // Load Parteien
        const parteienResult = await apiRequest('/wahlplakatgame/api/game/parteien', 'GET');
        
        if (parteienResult.success) {
            AppState.parteien = parteienResult.parteien;
            populateParteienDropdown(parteienResult.parteien);
        }
        
        // Update User Info
        updateUserInfo();
        
        // Show game page
        showPage('game');
        
        // Connect to WebSocket
        connectWebSocket();
        
    } catch (error) {
        console.error('Fehler beim Laden der Spiel-Seite:', error);
        showAlert('Fehler beim Laden des Spiels.');
        showPage('auth');
    } finally {
        showLoading(false);
    }
}

function populateParteienDropdown(parteien) {
    const dropdown = document.getElementById('partei-dropdown');
    dropdown.innerHTML = '';
    
    parteien.forEach(partei => {
        const option = document.createElement('option');
        option.value = partei;
        option.textContent = partei;
        dropdown.appendChild(option);
    });
}

function updateUserInfo() {
    document.getElementById('user-nickname').textContent = AppState.userInfo.nickname;
    document.getElementById('user-points').textContent = `Punkte: ${AppState.userInfo.points}`;
}

// ==================== WEBSOCKET CONNECTION ====================

function connectWebSocket() {
    console.log('🔌 Verbinde WebSocket...');
    addGameMessage('🔌 Verbinde mit Server...', 'info');
    
    // Connect to Socket.IO
    AppState.socket = io({
        path: '/wahlplakatgame/socket.io',
        transports: ['websocket', 'polling']
    });
    
    // Connection events
    AppState.socket.on('connect', onSocketConnect);
    AppState.socket.on('disconnect', onSocketDisconnect);
    AppState.socket.on('connected', onServerConnected);
    
    // Game events
    AppState.socket.on('join_success', onJoinSuccess);
    AppState.socket.on('new_round', onNewRound);
    AppState.socket.on('player_answered', onPlayerAnswered);
    AppState.socket.on('round_end', onRoundEnd);
    AppState.socket.on('player_joined', onPlayerJoined);
    AppState.socket.on('player_left', onPlayerLeft);
    AppState.socket.on('player_list_update', onPlayerListUpdate);
    AppState.socket.on('answer_accepted', onAnswerAccepted);
    AppState.socket.on('leaderboard_update', onLeaderboardUpdate);
    AppState.socket.on('error', onSocketError);
}

function onSocketConnect() {
    console.log('✅ WebSocket verbunden');
    
    // Join game
    AppState.socket.emit('join_game', {
        token: AppState.sessionToken
    });
}

function onSocketDisconnect() {
    console.log('🔌 WebSocket getrennt');
    addGameMessage('❌ Verbindung zum Server verloren', 'error');
}

function onServerConnected(data) {
    console.log('📡 Server:', data.message);
    addGameMessage('✅ Verbunden! Trete Lobby bei...', 'success');
}

// ==================== GAME EVENTS ====================

function onJoinSuccess(data) {
    console.log('🎉 Lobby beigetreten', data);
    addGameMessage('✅ Erfolgreich der Lobby beigetreten!', 'success');
    
    // Update player list
    updatePlayerList(data.players);
    
    // Request leaderboard
    AppState.socket.emit('request_leaderboard');
}

function onNewRound(data) {
    console.log('🎮 Neue Runde', data);
    
    GameState.hasAnswered = false;
    GameState.currentQuelle = null;
    GameState.canAnswer = true;
    
    // Enable answer button
    document.getElementById('answer-btn').disabled = false;
    document.getElementById('source-btn').disabled = true;
    
    // Add messages
    addGameMessage('\n' + '='.repeat(60), 'round-start');
    addGameMessage(`🎮 RUNDE #${data.round_number}`, 'round-start');
    addGameMessage('='.repeat(60) + '\n', 'round-start');
    addGameMessage(`"${data.wahlspruch}"\n`, 'info');
    addGameMessage('⏱️ 15 Sekunden Zeit zum Antworten!', 'info');
}

function onPlayerAnswered(data) {
    console.log('✓ Spieler hat geantwortet', data);
    addGameMessage(`✓ ${data.nickname} hat geantwortet`, 'info');
}

function onRoundEnd(data) {
    console.log('🏁 Runde beendet', data);
    
    GameState.currentQuelle = data.quelle;
    
    addGameMessage('\n' + '='.repeat(60), 'round-end');
    addGameMessage('🏁 RUNDENENDE', 'round-end');
    addGameMessage('='.repeat(60) + '\n', 'round-end');
    addGameMessage(`Richtige Antwort: ${data.correct_partei}\n`, 'success');
    
    // Check own result
    let myResult = null;
    for (const result of data.results) {
        if (result.nickname === AppState.userInfo.nickname) {
            myResult = result;
            break;
        }
    }
    
    // Play sound for own answer
    if (myResult) {
        if (myResult.correct === true) {
            playSound('correct');
        } else if (myResult.correct === false) {
            playSound('incorrect');
        }
    }
    
    // Show results
    for (const result of data.results) {
        if (!result.could_answer) {
            addGameMessage(`  ${result.nickname}: (während Runde beigetreten)`, 'info');
        } else if (result.correct === null) {
            addGameMessage(`  ${result.nickname}: Keine Antwort`, 'info');
        } else if (result.correct) {
            addGameMessage(`  ✓ ${result.nickname}: ${result.answered} [+${result.points_earned} Punkt] (Gesamt: ${result.total_points})`, 'success');
        } else {
            addGameMessage(`  ✗ ${result.nickname}: ${result.answered} (Gesamt: ${result.total_points})`, 'error');
        }
    }
    
    addGameMessage('\n⏳ Nächste Runde in 5 Sekunden...\n', 'info');
    
    // Update own points
    if (myResult) {
        AppState.userInfo.points = myResult.total_points;
        updateUserInfo();
    }
    
    // Enable source button if available
    if (GameState.currentQuelle) {
        document.getElementById('source-btn').disabled = false;
    }
}

function onPlayerJoined(data) {
    console.log('👋 Spieler beigetreten', data);
    addGameMessage(`👋 ${data.nickname} ist beigetreten`, 'warning');
    playSound('join');
}

function onPlayerLeft(data) {
    console.log('👋 Spieler verlassen', data);
    
    let message = `👋 ${data.nickname} hat die Lobby verlassen`;
    if (data.reason === 'disconnect') {
        message += ' (Verbindung getrennt)';
    }
    
    addGameMessage(message, 'warning');
    playSound('leave');
}

function onPlayerListUpdate(data) {
    updatePlayerList(data.players);
}

function onAnswerAccepted(data) {
    console.log('✅ Antwort akzeptiert', data);
    
    GameState.hasAnswered = true;
    document.getElementById('answer-btn').disabled = true;
    
    addGameMessage(`✅ Deine Antwort wurde registriert: ${data.partei}`, 'success');
    playSound('lock');
}

function onLeaderboardUpdate(data) {
    updateLeaderboard(data.leaderboard);
}

function onSocketError(data) {
    console.error('❌ Socket Error:', data);
    addGameMessage(`❌ Fehler: ${data.message}`, 'error');
}

// ==================== UI UPDATES ====================

function addGameMessage(text, type = 'default') {
    const gameBox = document.getElementById('game-box');
    const messageDiv = document.createElement('div');
    messageDiv.className = `game-message ${type}`;
    messageDiv.textContent = text;
    gameBox.appendChild(messageDiv);
    
    // Auto scroll to bottom
    gameBox.scrollTop = gameBox.scrollHeight;
}

function updatePlayerList(players) {
    const list = document.getElementById('players-list');
    list.innerHTML = '';
    
    if (players.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'Keine Spieler';
        list.appendChild(li);
        return;
    }
    
    players.forEach(player => {
        const li = document.createElement('li');
        
        let status = '⏳';
        if (player.answered) {
            status = '✓';
        } else if (!player.can_answer) {
            status = '⊘';
        }
        
        li.textContent = `${status} ${player.nickname} (${player.points})`;
        list.appendChild(li);
    });
}

function updateLeaderboard(leaderboard) {
    const list = document.getElementById('leaderboard-list');
    list.innerHTML = '';
    
    if (leaderboard.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'Keine Einträge';
        list.appendChild(li);
        return;
    }
    
    leaderboard.forEach(entry => {
        const li = document.createElement('li');
        
        let medal = '';
        if (entry.rank === 1) medal = '🥇';
        else if (entry.rank === 2) medal = '🥈';
        else if (entry.rank === 3) medal = '🥉';
        else medal = `${entry.rank}.`;
        
        li.textContent = `${medal} ${entry.nickname}: ${entry.points}`;
        list.appendChild(li);
    });
}

// ==================== USER ACTIONS ====================

function submitAnswer() {
    if (GameState.hasAnswered) {
        showAlert('Du hast bereits geantwortet!');
        return;
    }
    
    const selectedPartei = document.getElementById('partei-dropdown').value;
    
    if (!selectedPartei) {
        showAlert('Bitte wähle eine Partei aus!');
        return;
    }
    
    AppState.socket.emit('submit_answer', {
        token: AppState.sessionToken,
        partei: selectedPartei
    });
}

function showSource() {
    if (!GameState.currentQuelle) {
        showAlert('Keine Quelle verfügbar für diesen Wahlspruch.');
        return;
    }
    
    if (GameState.currentQuelle.startsWith('http')) {
        // Open URL in new tab
        window.open(GameState.currentQuelle, '_blank');
    } else {
        // Show as alert
        showAlert(`Quelle:\n\n${GameState.currentQuelle}`);
    }
}

function leaveGame() {
    if (!showConfirm('Möchtest du das Spiel wirklich verlassen?')) {
        return;
    }
    
    addGameMessage('👋 Verlasse Spiel...', 'warning');
    
    // Emit leave event
    if (AppState.socket && AppState.socket.connected) {
        AppState.socket.emit('leave_game', {
            token: AppState.sessionToken,
            reason: 'request'
        });
    }
    
    // Disconnect socket
    if (AppState.socket) {
        AppState.socket.disconnect();
        AppState.socket = null;
    }
    
    // Clear game box
    document.getElementById('game-box').innerHTML = '';
    
    // Back to auth
    showPage('auth');
}
