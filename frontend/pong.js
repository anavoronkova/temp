const canvas = document.getElementById('pong');
const ctx = canvas.getContext('2d');

console.log('Canvas Dimensions:', canvas.width, canvas.height);

const GAME_CONFIG = {
    paddleWidth: 15,
    paddleHeight: 100,
    ballDiameter: 20,
    paddleColor: '#FFFFFF',
    ballColor: '#FFFFFF',
    canvasWidth : canvas.width,
    canvasHeight : canvas.height,
};

const registrationScreen = document.getElementById('registration-screen');
const gameScreen = document.getElementById('game-screen');
const registrationForm = document.getElementById('registration-form');
const aliasInput = document.getElementById('alias-input');
const startButton = document.getElementById('start-button');

let playerAlias = '';

registrationForm.addEventListener('submit', (e) => {
    e.preventDefault();
    playerAlias = aliasInput.value.trim();

    if (playerAlias) {
        localStorage.setItem('playerAlias', playerAlias); // Save alias locally
        registrationScreen.classList.add('d-none');
        gameScreen.classList.remove('d-none'); // Show game screen
 //       startButton.classList.remove('d-none'); // Show Start Game button
    } else {
        alert("Please enter a valid alias!");
    }
});

let gameState = {
    paddles: {
        left: { y: GAME_CONFIG.canvasHeight / 2 - GAME_CONFIG.paddleHeight / 2, score: 0 },
        right: { y: GAME_CONFIG.canvasHeight / 2 - GAME_CONFIG.paddleHeight / 2, score: 0 },
    },
    ball: { x: GAME_CONFIG.canvasWidth / 2, y: GAME_CONFIG.canvasHeight / 2 },
};

const socket = new WebSocket('ws://localhost:8000/ws/game/room1/');

let isSocketOpen = false;

socket.onopen = function () {
    console.log("WebSocket connection established.");
    isSocketOpen = true;

    if (playerAlias) {
        sendAliasToBackend();
    }
    sendDimensions();
};

function sendDimensions() {
    const canvasConfig = {
        action: 'canvas_and_game_config',
        canvas: { width: GAME_CONFIG.canvasWidth, height: GAME_CONFIG.canvasHeight },
        paddle: { width: GAME_CONFIG.paddleWidth, height: GAME_CONFIG.paddleHeight },
        ball: { diameter: GAME_CONFIG.ballDiameter },
    };
    console.log("Sending canvas and game config:", canvasConfig);
    socket.send(JSON.stringify(canvasConfig));
}


socket.onclose = function () {
    console.log("WebSocket connection closed.");
    isSocketOpen = false;
};

socket.onerror = function (error) {
    console.error("WebSocket error:", error);
};

function sendAliasToBackend() {
    console.log(`Sending alias "${playerAlias}" to backend.`);
    socket.send(JSON.stringify({ action: 'start', player: playerAlias }));
}

startButton.addEventListener('click', () => {
    console.log("Start button clicked.");
    if (playerAlias) {
        socket.send(JSON.stringify({ action: 'start_game', player: playerAlias }));
        startButton.classList.add('d-none');
        canvas.classList.remove('d-none');
    } else {
        alert("Please register first.");
    }
});

socket.onmessage = function (event) {
    const data = JSON.parse(event.data);
    console.log("State update received:", data);

    if (data.type === 'state_update') {
        gameState = {
            ball: data.ball,
            paddles: data.paddles,
        };
        render();
    }
};


socket.onclose = function () {
    console.log("WebSocket connection closed.");
};

socket.onerror = function (error) {
    console.error("WebSocket error:", error);
};

document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowUp') {
        socket.send(JSON.stringify({ action: 'input', player: playerAlias, up: true, down: false }));
    } else if (e.key === 'ArrowDown') {
        socket.send(JSON.stringify({ action: 'input', player: playerAlias, up: false, down: true }));
    }
});

document.addEventListener('keyup', (e) => {
    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        socket.send(JSON.stringify({ action: 'input', player: playerAlias, up: false, down: false }));
    }
});

function drawRect(x, y, w, h, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, w, h);
}

function drawBall(x, y, radius, color) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.closePath();
    ctx.fill();
}

function clearCanvas() {
    ctx.clearRect(0, 0, GAME_CONFIG.canvasWidth, GAME_CONFIG.canvasHeight);
}

function render() {
    clearCanvas();

    drawRect(0, gameState.paddles.left.y, GAME_CONFIG.paddleWidth, GAME_CONFIG.paddleHeight, GAME_CONFIG.paddleColor);
    drawRect(
        GAME_CONFIG.canvasWidth - GAME_CONFIG.paddleWidth,
        gameState.paddles.right.y,
        GAME_CONFIG.paddleWidth,
        GAME_CONFIG.paddleHeight,
        GAME_CONFIG.paddleColor
    );

    drawBall(gameState.ball.x, gameState.ball.y, GAME_CONFIG.ballDiameter / 2, GAME_CONFIG.ballColor);

    ctx.font = '20px "Orbitron", sans-serif';
    ctx.fillStyle = 'white';
    ctx.textAlign = 'center';
    ctx.fillText(gameState.paddles.left.score, canvas.width / 4, 50);
    ctx.fillText(gameState.paddles.right.score, (canvas.width * 3) / 4, 50);
}

render();
