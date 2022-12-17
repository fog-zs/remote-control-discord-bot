import discord
from configparser import RawConfigParser
import subprocess
from requests import get
from os import path


class Bot(discord.Client):
    def __init__(self):
        self.config = RawConfigParser()
        self.config_path = 'config.ini'
        self.config.read(self.config_path)

        # Create a new Window
        subprocess.call(f"tmux new-window -t :1 -d", shell=True)
        subprocess.call(f"tmux send-keys -t :1 'cd' C-m", shell=True)

        # Connect discord
        intents = discord.Intents.all()
        super(Bot, self).__init__(intents=intents)

        # Number of display lines
        self.line_size = 3


    # Startup
    async def on_ready(self):
        print(f'Login: {self.user}')

        # Send readme
        # Delete already existing readme
        channel = self.get_channel(int(self.config['discord']['readme']))
        try:
            id = self.config['discord']['readme_msg']
            if id != "":
                msg = await channel.fetch_message(int(id))
                await msg.delete()
        except Exception as e:
            print(e)

        msg = f"**[Computer]**\n{self.config['discord']['reaction1']}: Console Restart\n{self.config['discord']['reaction2']}: Screen Display\nNumber of lines displayed: Please enter a number in the chat\nC-z: End of Program"
        msg_id = await channel.send(msg)
        await msg_id.add_reaction(self.config['discord']['reaction1'])
        await msg_id.add_reaction(self.config['discord']['reaction2'])

        self.config.set('discord', 'readme_msg', msg_id.id)
        with open(self.config_path, 'w') as file:
            self.config.write(file)


    # Message received
    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.channel.id == int(self.config['discord']['download']):
            await self.download(message)

        if message.channel.id == int(self.config['discord']['upload']):
            await self.upload(message)

        if message.channel.id == int(self.config['discord']['command']):
            await self.command(message)

        if message.channel.id == int(self.config['discord']['readme']):
            await self.set_line_size(message)


    # Press the reaction button
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id:
            return
        if payload.message_id != self.config['discord']['readme_msg']:
            return

        channel = self.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = self.get_user(payload.user_id)

        # Delete Reaction
        await message.remove_reaction(payload.emoji, user)

        if str(payload.emoji) == self.config['discord']['reaction1']:
            await self.restart()

        if str(payload.emoji) == self.config['discord']['reaction2']:
            await self.show_buffer()


    # Restart window 
    async def restart(self):        
        subprocess.call(f"tmux kill-window -t :1", shell=True)
        subprocess.call(f"tmux new-window -t :1 -d", shell=True)


    # Capture window
    async def show_buffer(self):        
        res = subprocess.run("tmux capture-pane -t :1 -p", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        msg = res.stdout.decode('utf-8')

        channel = self.get_channel(int(self.config['discord']['command']))
        if msg != "":
            print(msg)
            await channel.send(msg)


    # Set number of display lines
    async def set_line_size(self, message):
        msg = message.content
        if str.isdigit(msg):
            
            n = int(msg)
            if n < 1:
                n = 1
            self.line_size = n
            
            # Notice
            channel = self.get_channel(int(self.config['discord']['command']))
            msg = f"[Notice] Number of display lines set to {self.line_size} lines."
            print(msg)
            await channel.send(msg)
        await message.delete()


    # Send command
    async def command(self, message):
        msg = message.content
        print(f"[Command] {msg}")

        try:
            subprocess.call(f'tmux send-keys -t :1 "{msg}" C-m', shell=True)
            subprocess.call(f'tmux delete-buffer', shell=True)            
            res = subprocess.run("tmux capture-pane -t :1 -p", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            print(res.stdout)
            msg = res.stdout.decode('utf-8').split('\n')
            lines = '\n'.join(
                [line for line in msg if line != ""][-1-self.line_size:])
            if lines == "" or lines == None:
                return
            print(lines)
            await message.channel.send(lines)

        except Exception as e:
            msg = f"[Command] {e}"
            print(msg)
            await message.channel.send(msg)


    # Download from server
    async def download(self, message):
        print(f"[Download] {message.content}")
        try:
            await message.channel.send(file=discord.File(message.content))
        except Exception as e:
            msg = f"[Download] {e}"
            print(msg)
            await message.channel.send(msg)


    # Upload to server
    async def upload(self, message):
        try:
            url = message.attachments[0].url
            print(f"[Upload] {url}")

            response = get(url)
            p = f"{path.basename(url)}"
            file = open(p, "wb")
            file.write(response.content)
            file.close()

            msg = f"[Upload] Sucess {p}"
            print(msg)
            await message.channel.send(msg)

        except Exception as e:
            msg = f"[Upload] {e}"
            print(msg)
            await message.channel.send(msg)


if __name__ == "__main__":
    bot = Bot()
    bot.run(bot.config['discord']['token'])
