# backend/apps/game/consumers.py
import asyncio
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from .gamemanager import GameManager

logger = logging.getLogger(__name__)

# Create a global instance of GameManager
# In a production setting, you might start it elsewhere and import that instance.
game_manager = GameManager()

class GameConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"game_{self.room_name}"

        logger.info(f"WebSocket connect: room={self.room_name}, channel={self.channel_name}")
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Ensure the GameManager is running
        asyncio.get_event_loop().create_task(game_manager.start())

        # Add player to the room via the GameManager
        game_manager.add_player(self.room_name, self.channel_name)

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnect: room={self.room_name}, channel={self.channel_name}, close_code={close_code}")
        game_manager.remove_player(self.room_name, self.channel_name)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        logger.info(f"WebSocket receive: room={self.room_name}, data={text_data}")
        data = json.loads(text_data)
        action = data.get('action')
        player_alias = data.get('player')

        if player_alias:
            game_manager.set_player_alias(self.room_name, self.channel_name, player_alias)

        if action == 'input':
            up = data.get('up', False)
            down = data.get('down', False)
            game_manager.update_player_input(self.room_name, self.channel_name, up, down)

    async def game_message(self, event):
        # Called by group_send in GameManager
        await self.send(text_data=json.dumps(event['data']))