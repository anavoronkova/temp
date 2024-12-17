let playerAlias = '';

const registrationScreen = document.getElementById('registration-screen');
const gameScreen = document.getElementById('game-screen');
const registrationForm = document.getElementById('registration-form');
const aliasInput = document.getElementById('alias-input');

registrationForm.addEventListener('submit', (e) => {
    e.preventDefault(); // Prevent the form from refreshing the page
    playerAlias = aliasInput.value.trim();

    if (playerAlias) {
        localStorage.setItem('playerAlias', playerAlias);
        registrationScreen.classList.add('d-none');
        gameScreen.classList.remove('d-none');
        startButton.classList.remove('d-none'); 
    } else {
        alert('Please enter a valid alias!');
    }
});

const canvas = document.getElementById('pong');
const ctx = canvas.getContext('2d');
const startButton = document.getElementById('start-button');

// Define paddles, ball, and game state
const paddleWidth = 10;
const paddleHeight = 100;
const ballSize = 10;

const player = { x: 0, y: canvas.height / 2 - paddleHeight / 2, score: 0 };
const ai = { x: canvas.width - paddleWidth, y: canvas.height / 2 - paddleHeight / 2, score: 0 };
const ball = { x: canvas.width / 2, y: canvas.height / 2, vx: 4, vy: 4 };

startButton.addEventListener('click', () => {
    startButton.classList.add('d-none');
    canvas.classList.remove('d-none');
});

// Key states for player movement
const keys = { up: false, down: false };

// Draw game objects
function drawRect(x, y, w, h, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, w, h);
}

function drawBall(x, y, radius, color) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2); // Draw a circle
    ctx.closePath();
    ctx.fill();
}


// Reset ball after scoring
function resetBall() {
    ball.x = canvas.width / 2;
    ball.y = canvas.height / 2;
    ball.vx = 4 * (Math.random() > 0.5 ? 1 : -1);
    ball.vy = 4 * (Math.random() > 0.5 ? 1 : -1);
}

const socket = new WebSocket('ws://localhost:8000/ws/game/room1/');

// Maintain local state only for rendering
let gameState = {
    paddles: {
        left: { y: 100, score: 0 },
        right: { y: 100, score: 0 }
    },
    ball: { x: 300, y: 150 }
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
        // When key is released, send no movement
        socket.send(JSON.stringify({ action: 'input', player: playerAlias, up: false, down: false }));
    }
});

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'state_update') {
        // Update local state
        gameState = {
            ...gameState,
            ball: data.ball,
            paddles: data.paddles
        };
        render();
    }
};

function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw paddles
    drawRect(0, gameState.paddles.left.y, paddleWidth, paddleHeight, 'white');
    drawRect(canvas.width - paddleWidth, gameState.paddles.right.y, paddleWidth, paddleHeight, 'white');

    // Draw ball
    drawBall(gameState.ball.x, gameState.ball.y, ballSize / 2, 'white');

    // Draw names and scores if needed
    ctx.fillStyle = 'white';
    ctx.font = '20px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(playerAlias || 'Player', canvas.width / 4, 30);
    ctx.fillText('Opponent', (canvas.width * 3) / 4, 30);

    ctx.fillText(gameState.paddles.left.score, canvas.width / 4, 60);
    ctx.fillText(gameState.paddles.right.score, (canvas.width * 3) / 4, 60);
}

socket.onopen = function() {
    console.log("WebSocket is open now.");
    // Send a message to the server. Note that your server expects a 'player' key.
    const currentAlias = localStorage.getItem('playerAlias') || 'UnknownPlayer';
    socket.send(JSON.stringify({ action: 'start', player: currentAlias }));
};
