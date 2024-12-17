import asyncio
import logging
import time
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

class GameManager:
    TICK_RATE = 60

    def __init__(self):
        self.games = {}
        self.running = False
        self.channel_layer = None 

    async def start(self):
        """Start the main game loop."""
        if self.running:
            return
        self.running = True
        logger.info("GameManager started.")
        
        # Initialize channel layer here
        if not self.channel_layer:
            self.channel_layer = get_channel_layer()
        
        await self.game_loop()

    async def game_loop(self):
        """Run a central loop that updates all active games."""
        next_frame_time = time.perf_counter()
        frame_duration = 1.0 / self.TICK_RATE
        broadcast_interval = 0.1  # 100ms
        last_broadcast_time = 0

        while self.running:
            start = time.perf_counter()
            dt = start - next_frame_time + frame_duration

            self.update_all_games(dt)

            if start - last_broadcast_time >= broadcast_interval:
                await self.broadcast_all_states()
                last_broadcast_time = start

            next_frame_time += frame_duration
            sleep_duration = next_frame_time - time.perf_counter()
            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration)

    def create_or_get_game(self, room_name):
        if room_name not in self.games:
            self.games[room_name] = self.initial_game_state()
            logger.info(f"Created new game state for room: {room_name}")
        return self.games[room_name]

    def remove_game(self, room_name):
        if room_name in self.games:
            del self.games[room_name]
            logger.info(f"Removed game state for room: {room_name}")

    def add_player(self, room_name, channel_name):
        game = self.create_or_get_game(room_name)
        players = game['players']
        side = 'left' if len(players) == 0 else 'right'
        players[channel_name] = {
            'side': side,
            'input': {'up': False, 'down': False},
            'alias': None
        }
        logger.info(f"Player {channel_name} joined room {room_name} as {side}")

    def remove_player(self, room_name, channel_name):
        game = self.games.get(room_name)
        if not game:
            return
        if channel_name in game['players']:
            del game['players'][channel_name]
            logger.info(f"Player {channel_name} left room {room_name}")

        if len(game['players']) == 0:
            self.remove_game(room_name)

    def update_player_input(self, room_name, channel_name, up, down):
        game = self.games.get(room_name)
        if game and channel_name in game['players']:
            game['players'][channel_name]['input']['up'] = up
            game['players'][channel_name]['input']['down'] = down

    def set_player_alias(self, room_name, channel_name, alias):
        game = self.games.get(room_name)
        if game and channel_name in game['players']:
            game['players'][channel_name]['alias'] = alias


    def initial_game_state(self):
        return {
            'players': {},
            'ball': {'x': 400, 'y': 150, 'vx': 4, 'vy': 4},
            'paddles': {
                'left': {'y': 100, 'score': 0},
                'right': {'y': 100, 'score': 0}
            },
            'canvas': {'width': 800, 'height': 400},
        }

    def update_all_games(self, dt):
        for room_name, game_state in self.games.items():
            self.update_game_state(game_state, dt)

    def set_game_config(self, room_name, canvas, paddle, ball):
        """Set canvas, paddle, and ball sizes for a specific room."""
        game = self.create_or_get_game(room_name)
        game['canvas'] = canvas
        game['config'] = {
            'paddle': paddle,
            'ball': ball
        }
        logger.info(f"Game config set for room '{room_name}': canvas={canvas}, paddle={paddle}, ball={ball}")

    def update_game_state(self, game_state, dt):
        canvas = game_state.get('canvas', {'width': 800, 'height': 400})
        paddle = game_state.get('config', {}).get('paddle', {'width': 15, 'height': 100})
        ball = game_state.get('config', {}).get('ball', {'diameter': 20})

        paddle_speed = 6
        max_paddle_y = canvas['height'] - paddle['height']

        # Update paddle positions based on player input
        for player_data in game_state['players'].values():
            side = player_data['side']
            input_data = player_data['input']
            if input_data['up']:
                game_state['paddles'][side]['y'] -= paddle_speed
            if input_data['down']:
                game_state['paddles'][side]['y'] += paddle_speed

            # Clamp paddles to ensure they stay within canvas boundaries
            if game_state['paddles'][side]['y'] < 0:
                game_state['paddles'][side]['y'] = 0
            if game_state['paddles'][side]['y'] > max_paddle_y:
                game_state['paddles'][side]['y'] = max_paddle_y

        # Update ball position
        ball_state = game_state['ball']
        ball_state['x'] += ball_state['vx']
        ball_state['y'] += ball_state['vy']

        # Handle ball collisions with canvas borders
        if ball_state['y'] <= 0 or ball_state['y'] >= canvas['height'] - ball['diameter']:
            ball_state['vy'] = -ball_state['vy']

        # Check for ball collisions with paddles
        left_paddle = game_state['paddles']['left']
        right_paddle = game_state['paddles']['right']

        if (ball_state['x'] <= paddle['width'] and
            left_paddle['y'] <= ball_state['y'] <= left_paddle['y'] + paddle['height']):
            ball_state['vx'] = -ball_state['vx']

        if (ball_state['x'] >= canvas['width'] - paddle['width'] - ball['diameter'] and
            right_paddle['y'] <= ball_state['y'] <= right_paddle['y'] + paddle['height']):
            ball_state['vx'] = -ball_state['vx']

        # Scoring logic
        if ball_state['x'] < 0:  # Ball exits on the left
            right_paddle['score'] += 1
            self.reset_ball(ball_state, canvas, ball)
        if ball_state['x'] > canvas['width']:  # Ball exits on the right
            left_paddle['score'] += 1
            self.reset_ball(ball_state, canvas, ball)

    def reset_ball(self, ball, canvas, ball_config):
        """Reset ball position to the center of the canvas."""
        logger.info(f"Resetting ball: previous_position={ball}")
        ball['x'] = canvas['width'] // 2
        ball['y'] = canvas['height'] // 2
        ball['vx'] = 4 * (-1 if ball['vx'] > 0 else 1)
        ball['vy'] = 4 * (-1 if ball['vy'] > 0 else 1)

    async def broadcast_all_states(self):
        for room_name, game_state in self.games.items():
            message = {
                'type': 'state_update',
                'ball': game_state['ball'],  # Ball position
                'paddles': game_state['paddles'],  # Paddle positions
            }
            await self.channel_layer.group_send(
                f"game_{room_name}",
                {
                    'type': 'game_message',
                    'data': message,
                }
            )


# Export a singleton instance of GameManager
game_manager = GameManager()