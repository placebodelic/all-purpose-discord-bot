import discord
from discord.ext import commands
from openai import OpenAI
import os
from dotenv import load_dotenv
import sqlite3
from datetime import datetime, timedelta


load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

conn = sqlite3.connect('conversation_history.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS messages
             (user_id INTEGER, content TEXT, role TEXT, timestamp DATETIME)''')
conn.commit()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

def get_conversation_history(user_id):
    one_day_ago = datetime.now() - timedelta(days=1)
    c.execute("SELECT content, role FROM messages WHERE user_id = ? AND timestamp > ? ORDER BY timestamp ASC",
              (user_id, one_day_ago))
    return [{"role": role, "content": content} for content, role in c.fetchall()]

def add_to_history(user_id, content, role):
    c.execute("INSERT INTO messages VALUES (?, ?, ?, ?)",
              (user_id, content, role, datetime.now()))
    conn.commit()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        question = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()

        try:
            history = get_conversation_history(message.author.id)
            history.append({"role": "user", "content": question})
            add_to_history(message.author.id, question, "user")

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that is in a discord chat. Please provide concise answers without unnecessary preamble. Focus directly on the question asked. Assume I have a basic understanding of the topic. Skip introductory explanations and go straight to the specific solution. Do not repeat the question or provide background information unless specifically requested. Keep responses under three sentences unless more detail is explicitly requested. Always reply in lowercase. "},
                ] + history
            )
            answer = response.choices[0].message.content
            add_to_history(message.author.id, answer, "assistant")
            await message.channel.send(answer)
        except Exception as e:
            await message.channel.send(f"an error occurred: {str(e)}")

    await bot.process_commands(message)

@bot.command(name='clear_history')
async def clear_history(ctx):
    c.execute("DELETE FROM messages WHERE user_id = ?", (ctx.author.id,))
    conn.commit()
    await ctx.send("your conversation history has been cleared.")
  
discord_token = os.getenv('DISCORD_TOKEN')
if discord_token is None:
    raise ValueError("DISCORD_TOKEN environment variable is not set")
bot.run(discord_token)
