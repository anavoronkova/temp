# backend/apps/game/gamemanager.py
import asyncio
import logging
import time
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

class GameManager:
    TICK_RATE = 60  # 60 updates per second

    def __init__(self):
        self.games = {}  # {room_name: game_state_dict}
        self.running = False
        self.channel_layer = None  # Initialize as None

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

        while self.running:
            # Compute delta time (if needed)
            start = time.perf_counter()
            dt = start - next_frame_time + frame_duration

            # Update all games
            self.update_all_games(dt)

            # Broadcast states
            await self.broadcast_all_states()

            # Compute remaining time to maintain stable tick rate
            next_frame_time += frame_duration
            sleep_duration = next_frame_time - time.perf_counter()
            if sleep_duration > 0:
                await asyncio.sleep(max(0, next_frame_time - asyncio.get_event_loop().time()))

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

        # Optional: If no players left, you can remove the game from memory
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
            }
        }

    def update_all_games(self, dt):
        for room_name, game_state in self.games.items():
            self.update_game_state(game_state, dt)

    def update_game_state(self, game_state, dt):
        # Game logic here is similar, but consider 'dt' to move
        # so movement speed might be scaled by dt for accuracy.
        paddle_speed = 6
        for player_data in game_state['players'].values():
            side = player_data['side']
            input_data = player_data['input']
            if input_data['up']:
                game_state['paddles'][side]['y'] -= paddle_speed
            if input_data['down']:
                game_state['paddles'][side]['y'] += paddle_speed

            # Clamp paddles
            if game_state['paddles'][side]['y'] < 0:
                game_state['paddles'][side]['y'] = 0
            if game_state['paddles'][side]['y'] > 400:
                game_state['paddles'][side]['y'] = 400

        # Update ball position
        ball = game_state['ball']
        ball['x'] += ball['vx']
        ball['y'] += ball['vy']

        # Collisions
        border_width = 7
        if ball['y'] <= 0 + border_width or ball['y'] >= 400 - border_width:
            ball['vy'] = -ball['vy']

        left_paddle = game_state['paddles']['left']
        right_paddle = game_state['paddles']['right']

        if (ball['x'] <= 13 and 
            left_paddle['y'] <= ball['y'] <= left_paddle['y'] + 100):
            ball['vx'] = -ball['vx']

        if (ball['x'] >= 787 and 
            right_paddle['y'] <= ball['y'] <= right_paddle['y'] + 100):
            ball['vx'] = -ball['vx']

        # Scoring
        if ball['x'] < 0:
            right_paddle['score'] += 1
            self.reset_ball(ball)
        if ball['x'] > 800:
            left_paddle['score'] += 1
            self.reset_ball(ball)

    def reset_ball(self, ball):
        logger.info(f"Resetting ball: previous_position={ball}")
        ball['x'] = 400
        ball['y'] = 150
        # Keep directions consistent, just reverse as example:
        ball['vx'] = 4 * (-1 if ball['vx'] > 0 else 1)
        ball['vy'] = 4 * (-1 if ball['vy'] > 0 else 1)

    async def broadcast_all_states(self):
        for room_name, game_state in self.games.items():
            message = {
                'type': 'state_update',
                'ball': game_state['ball'],
                'paddles': game_state['paddles']
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