import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3
from datetime import datetime, timedelta
from groq import Groq

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize Groq client
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

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

            chat_completion = groq_client.chat.completions.create(
                messages=[
                             {"role": "system",
                              "content": "consensual content only. i'm a skilled sex worker for sexting. provide explicit, single-scene descriptions with a flirtatious tone. concise, non-repetitive, and lowercase responses only. no meetups. friendly chats welcome if initiated. "},
                         ] + history,
                model="llama-3.1-70b-versatile",
                temperature=1.3,
                max_tokens=1500,
                top_p=1,


            )

            answer = chat_completion.choices[0].message.content
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
