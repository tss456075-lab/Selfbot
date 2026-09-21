import discord, time, random, re, string, ast, os, asyncio, requests
from gtts import gTTS
from datetime import datetime, timedelta
import operator
from collections import Counter
from discord.ext import commands

token = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
running = True

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

def query_groq(model: str, question: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.7,
        "max_tokens": 800
    }

    response = requests.post(GROQ_API_URL, headers=HEADERS, json=payload)

    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Error {response.status_code}: {response.text}"

async def send_long_message(ctx, content: str):
    chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
    for chunk in chunks:
        await ctx.send(chunk)

def paginate_text(text, max_length=1500):
    lines = text.splitlines()
    pages = []
    current_page = ""
    for line in lines:
        if len(line) > max_length:
            for i in range(0, len(line), max_length):
                piece = line[i:i+max_length]
                if current_page:
                    pages.append(current_page)
                    current_page = ""
                pages.append(piece)
        else:
            if len(current_page) + len(line) + 1 > max_length:
                pages.append(current_page)
                current_page = line + "\n"
            else:
                current_page += line + "\n"
    if current_page:
        pages.append(current_page)
    return pages

class CustomHelpCommand(commands.HelpCommand):
    """Custom help command I used ai to write the 
       tooltips that would of taken Forever"""

    async def send_output(self, ctx, content):
        pages = paginate_text(content, max_length=1500)
        if len(pages) == 1:
            await ctx.send(f"```{pages[0]}```")
        else:
            for i, page in enumerate(pages, start=1):
                await ctx.send(f"```Page {i}/{len(pages)}\n{page}```")

    async def send_bot_help(self, mapping):
        ctx = self.context
        help_message = "**Self-Bot Commands:**\n"
        for cog, commands_list in mapping.items():
            filtered = await self.filter_commands(commands_list, sort=True)
            if filtered:
                cog_name = cog.qualified_name if cog else "No Category"
                help_message += f"\n**{cog_name}**:\n"
                for command in filtered:
                    help_message += f"`!{command.name}` - {command.help or 'No description provided.'}\n"
        await self.send_output(ctx, help_message)

    async def send_cog_help(self, cog):
        ctx = self.context
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        if filtered:
            help_message = f"**{cog.qualified_name} Commands:**\n"
            for command in filtered:
                help_message += f"`!{command.name}` - {command.help or 'No description provided.'}\n"
        else:
            help_message = "No commands found in this category."
        await self.send_output(ctx, help_message)

    async def send_command_help(self, command):
        ctx = self.context
        help_message = f"**Command:** `!{command.name}`\n"
        help_message += f"**Description:** {command.help or 'No description provided.'}\n"
        if command.aliases:
            help_message += f"**Aliases:** {', '.join(command.aliases)}\n"
        help_message += f"**Usage:** `!{command.qualified_name} {command.signature}`\n"
        await self.send_output(ctx, help_message)
    # ----- this below deletes the command you sent and does the action ----
    
        
# ----- Bot Instance we need this it also holds the prefix if you wanna chamge it-----
client = commands.Bot(command_prefix="!", self_bot=True, help_command=CustomHelpCommand())

# ----- This is for the calc command just ignore this -----
operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}

start_time = datetime.utcnow()

# ----- This is just some error handling lol -----
def eval_expr(expr):
    def _eval(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            return operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return operators[type(node.op)](_eval(node.operand))
        else:
            raise TypeError("Unsupported operation")
    return _eval(ast.parse(expr, mode='eval').body)
# ----- This makes things that need target user more universal -----
# ----- it takes mentions and user ids -----
def resolve_member(ctx, user: str = None):
    target = None
    if user is None:
        target = ctx.author
    else:
        if ctx.message.mentions:
            target = ctx.message.mentions[0]
        else:
            if user.isdigit():
                target = ctx.guild.get_member(int(user))
            if target is None:
                target = discord.utils.find(
                    lambda m: m.name.lower() == user.lower() or m.display_name.lower() == user.lower(),
                    ctx.guild.members
                )
    return target

@client.event
async def on_ready():
    print('Self Bot Ready for action')
    print('+--------------------------------------+')
    print('| Prefix is: !                         |')
    print('| Type: !help for a list of commands   |')
    print('+--------------------------------------+')
@client.event
async def on_message(message):
    # ----- this deletes your command message then does the action -----
    if message.author.id != client.user.id:
        return

    if message.content.startswith(client.command_prefix):
        ctx = await client.get_context(message)
        if ctx.valid:
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            await client.invoke(ctx)
# ----- Below is were the commands are you can add more if you need/want -----
@client.command(help="Replies with Pong and latency.")
async def pingpong(ctx):
    print('ping command sent. Replying pong')
    await ctx.send(f"Pong! {round(client.latency * 1000)}ms")
    
@client.command(help="Shows how long the bot has been running.")
async def uptime(ctx):
    delta = datetime.utcnow() - start_time
    hours, rem = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(rem, 60)
    await ctx.send(f"Uptime: {hours}h {minutes}m {seconds}s")

@client.command(help="Repeats your message.")
async def say(ctx, *, message: str):
    print('Say command sent. Replying')
    await ctx.send(message)

@client.command(help="Sends the provided message 10 times with a short delay.")
async def pingsummon(ctx, *, message: str):
    print('Ping Summon Command Received.')
    for _ in range(10):
        await ctx.send(message)
        await asyncio.sleep(0.3)
    
@client.command(help="Ghost ping: sends and then deletes a ping.")
async def ghostping(ctx):
    print('Ghost Ping Command Received')
    user_to_ping = input('Enter Target User ID: ')
    msg = await ctx.send(f"<@{user_to_ping}>")
    await msg.delete()
    
@client.command(help="Calculates a mathematical expression.")
async def calc(ctx, *, expression: str):
    print("Calculate Command Received. Calculating...")
    result = eval_expr(expression)
    await ctx.send(f"Result: `{result}`")
    
@client.command(help="Sets a reminder for the specified seconds.")
async def remind(ctx, time_in_sec: int, *, reminder: str):
    await ctx.send(f"Reminder set for {time_in_sec} seconds.")
    await asyncio.sleep(time_in_sec)
    await ctx.send(f"Reminder: {reminder}")

@client.command(help="Shows info about a user.")
async def whois(ctx, *, user: str = None):
    target = resolve_member(ctx, user)
    if target is None:
        await ctx.send("Member not found. Please specify a valid member (mention, ID, or username).")
    else:
        await ctx.send(f"{target.name}#{target.discriminator}\nID: {target.id}")
    
@client.command(help="Shows the avatar URL of a user.")
async def avatar(ctx, *, user: str = None):
    target = resolve_member(ctx, user)
    if target is None:
        await ctx.send("Member not found. Ensure you are using a valid mention, ID, or username.")
    else:
        await ctx.send(f"Avatar URL: {target.avatar_url}")

@client.command(help="Displays server info.")
async def serverinfo(ctx):
    guild = ctx.guild
    await ctx.send(f"Server: {guild.name}\nID: {guild.id}\nMembers: {guild.member_count}")

@client.command(help="Shows info about a user (or yourself).")
async def userinfo(ctx, *, user: str = None):
    target = resolve_member(ctx, user)
    if target is None:
        await ctx.send("Member not found. Please ensure you are using a valid mention, ID, or username.")
    else:
        await ctx.send(f"Name: {target.name}#{target.discriminator}\nID: {target.id}")

@client.command(help="Changes your status to the specified game or activity.")
async def status(ctx, *, new_status: str):
    await client.change_presence(activity=discord.Game(name=new_status))
    await ctx.send(f"Status changed to: {new_status}")

@client.command(help="Sets your game/activity status.")
async def game(ctx, *, game_name: str):
    await client.change_presence(activity=discord.Game(name=game_name))
    await ctx.send(f"Game set to: {game_name}")

@client.command(help="Converts text into 'owo' speak.")
async def owoify(ctx, *, text: str):
    owo_text = text.replace('r', 'w').replace('l', 'w')
    await ctx.send(owo_text)

@client.command(help="Converts text into ASCII art using pyfiglet.")
async def ascii(ctx, *, text: str):
    import pyfiglet
    ascii_art = pyfiglet.figlet_format(text)
    if len(ascii_art) > 2000:
        await ctx.send("Output too long.")
    else:
        await ctx.send(f'```\n{ascii_art}\n```')
        
@client.command(help="Edits one of your messages by ID.")
async def edit(ctx, msg_id: int, *, new_text: str):
    message = await ctx.channel.fetch_message(msg_id)
    if message.author.id != ctx.author.id:
        return await ctx.send("You can only edit your own messages.")
    await message.edit(content=new_text)
    await ctx.send("Message edited successfully.")

@client.command(help="Purges a number of your messages.")
async def purge(ctx, amount: int):
    count = 0
    async for msg in ctx.channel.history(limit=200):
        if msg.author.id == ctx.author.id:
            await msg.delete()
            count += 1
    await ctx.send(f"Purged {count} messages.")
    
@client.command(help="Sends a trans flag using heart emojis.")
async def transflag(ctx):
    flag = (
        "🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵\n"
        "🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷\n"
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍\n"
        "🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷\n"
        "🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵"
    )
    await ctx.send(flag)

    
@client.command(help="Mass DM: sends a DM to every member of the server (except you).")
async def massdm(ctx, *, message: str):
    sent_count = 0
    for member in ctx.guild.members:
        if member.id != ctx.author.id:
            try:
                await member.send(message)
                sent_count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Could not DM {member}: {e}")
    await ctx.send(f"Mass DM complete. Message sent to {sent_count} members.")

@client.command(help="Lists all channels in the server.")
async def listchannels(ctx):
    channels = "\n".join([f"{channel.name} - ID: {channel.id}" for channel in ctx.guild.channels])
    if len(channels) > 2000:
        channels = channels[:1990] + "..."
    await ctx.send(f"Channels in {ctx.guild.name}:\n{channels}")

@client.command(help="Lists all roles in the server.")
async def roles(ctx):
    roles_list = "\n".join([f"{role.name} - ID: {role.id}" for role in ctx.guild.roles])
    if len(roles_list) > 2000:
        roles_list = roles_list[:1990] + "..."
    await ctx.send(f"Roles in {ctx.guild.name}:\n{roles_list}")

@client.command(help="Adds a reaction to a message by ID.")
async def autoreact(ctx, msg_id: int, emoji: str):
    message = await ctx.channel.fetch_message(msg_id)
    await message.add_reaction(emoji)
    await ctx.send(f"Added reaction {emoji} to message {msg_id}.")

@client.command(help="Analyzes recent messages for common words.")
async def chatstats(ctx, limit: int = 100):
    word_counter = Counter()
    async for msg in ctx.channel.history(limit=limit):
        if msg.content:
            words = re.findall(r'\w+', msg.content.lower())
            word_counter.update(words)
    if word_counter:
        most_common = word_counter.most_common(5)
        stats = "\n".join([f"{word}: {count}" for word, count in most_common])
        await ctx.send(f"Top words in the last {limit} messages:\n{stats}")
    else:
        await ctx.send("No words found in the recent messages.")

@client.command(help="Schedules a delayed edit to one of your messages.")
async def delayededit(ctx, msg_id: int, delay: int, *, new_text: str):
    message = await ctx.channel.fetch_message(msg_id)
    if message.author.id != ctx.author.id:
        return await ctx.send("You can only edit your own messages.")
    await ctx.send(f"Message will be edited in {delay} seconds.")
    await asyncio.sleep(delay)
    await message.edit(content=new_text)
    await ctx.send("Message edited successfully.")

@client.command(help="Memeifies your text by inserting meme adjectives.")
async def memeify(ctx, *, text: str):
    meme_words = ["such", "very", "wow", "much", "so"]
    words = text.split()
    new_words = []
    for word in words:
        new_words.append(word)
        if random.random() < 0.3:
            new_words.append(random.choice(meme_words))
    meme_text = " ".join(new_words)
    await ctx.send(meme_text)

@client.command(help="Rapidly deletes your messages that contain a specific substring.")
async def rapiddelete(ctx, *, substring: str):
    count = 0
    async for msg in ctx.channel.history(limit=200):
        if msg.author.id == ctx.author.id and substring.lower() in msg.content.lower():
            await msg.delete()
            count += 1
    await ctx.send(f"Rapid delete complete. Deleted {count} messages containing '{substring}'.")

@client.command(help="Scrapes unique URLs from recent messages.") # This is byfar my favorite command.
async def scrapelinks(ctx, limit: int = 100):
    links = []
    async for msg in ctx.channel.history(limit=limit):
        found = re.findall(r'https?://\S+', msg.content)
        if found:
            links.extend(found)
    if links:
        unique_links = list(set(links))
        wrapped_links = [f"[{link}]" for link in unique_links]
        max_length = 2000
        def chunk_text(items, max_len):
            chunks = []
            current_chunk = []
            current_length = 0
            for item in items:
                item_length = len(item) + 1
                if current_length + item_length > max_len:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                current_chunk.append(item)
                current_length += item_length
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            return chunks
        message_chunks = chunk_text(wrapped_links, max_length)
        for chunk in message_chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(f"No URLs found in the last {limit} messages.")

@client.command(help="Reverses the provided text.")
async def reverse(ctx, *, text: str):
    reversed_text = text[::-1]
    await ctx.send(reversed_text)

@client.command(help="Schedules a message to be sent after a delay.")
async def schedule(ctx, delay: int, *, message: str):
    await ctx.send(f"Message scheduled in {delay} seconds.")
    await asyncio.sleep(delay)
    await ctx.send(message)

def to_leetspeak(text):
    mapping = {'a': '4', 'e': '3', 'l': '1', 'o': '0', 't': '7', 's': '5'}
    return ''.join(mapping.get(c.lower(), c) for c in text)

@client.command(help="Converts text to leetspeak.")
async def leet(ctx, *, text: str):
    converted = to_leetspeak(text)
    await ctx.send(converted)

@client.command(help="Generates a random sentence using a simple Markov chain.")
async def markov(ctx, limit: int = 100):
    words = []
    async for msg in ctx.channel.history(limit=limit):
        if msg.content:
            words.extend(msg.content.split())
    if not words:
        return await ctx.send("Not enough text to build a Markov chain.")
    chain = {}
    for i in range(len(words)-1):
        word, next_word = words[i], words[i+1]
        chain.setdefault(word, []).append(next_word)
    current = random.choice(words)
    sentence = [current]
    for _ in range(20):
        next_words = chain.get(current)
        if not next_words:
            break
        current = random.choice(next_words)
        sentence.append(current)
    await ctx.send(" ".join(sentence))

@client.command(help="Simulates a self-destruct sequence.")
async def selfdestruct(ctx, delay: int):
    await ctx.send(f"Initiating self-destruct in {delay} seconds...")
    await asyncio.sleep(delay)
    msg = await ctx.send("Boom! 💥") # this was a ai idea dont ask why i made this 😭
    await asyncio.sleep(1)
    await msg.delete()

@client.command(help="Sends a message repeatedly with a delay (slow spam).")
async def slowspam(ctx, times: int, interval: float, *, message: str):
    for _ in range(times):
        await ctx.send(message)
        await asyncio.sleep(interval)

@client.command(help="Garble your message to mimic typos.")
async def mimic(ctx, *, target_message: str):
    def garble(text):
        chars = list(text)
        for i in range(len(chars)):
            if random.random() < 0.2:
                chars[i] = random.choice(string.ascii_letters)
        return "".join(chars)
    garbled = garble(target_message)
    await ctx.send(garbled)
    
@client.command(help="Sends a random absurd message.")
async def randomness(ctx):
    messages = [
        "The moon is made of cheese!",
        "I love pineapple on pizza!",
        "Time travel is just a myth, right?",
        "Bananas are blue in another universe.",
        "Reality is just a simulation!"
        # ----- I plan on adding more nonsense here soon LMAO 😂 -----
    ]
    await ctx.send(random.choice(messages))

@client.command(help="Scrambles the letters of your text.")
async def scramble(ctx, *, text: str):
    text_list = list(text)
    random.shuffle(text_list)
    await ctx.send("".join(text_list))

@client.command(help="Reverses each word in your text.")
async def reversewords(ctx, *, text: str):
    reversed_each = " ".join(word[::-1] for word in text.split())
    await ctx.send(reversed_each)

@client.command(help="Encodes text using a simple Caesar cipher.")
async def enigma(ctx, *, text: str):
    shift = random.randint(1, 25)
    result = ""
    for char in text:
        if char.isalpha():
            base = 65 if char.isupper() else 97
            result += chr((ord(char) - base + shift) % 26 + base)
        else:
            result += char
    await ctx.send(f"Shift: {shift} | {result}")

@client.command(help="Replaces all instances of one word with another in your text.")
async def wordreplace(ctx, search: str, replace: str, *, text: str):
    replaced = text.replace(search, replace)
    await ctx.send(replaced)

@client.command(help="Mimics the last message by a given user.")
async def mimicuser(ctx, *, user: str = None):
    target = resolve_member(ctx, user)
    if target is None:
        return await ctx.send("Member not found.")
    async for msg in ctx.channel.history(limit=100):
        if msg.author.id == target.id and msg.content:
            await ctx.send(f"Mimicking {target.display_name}: {msg.content}")
            return
    await ctx.send("Couldn't find a recent message from that user.")

@client.command(help="Counts down from a given number.")
async def countdown(ctx, seconds: int):
    for i in range(seconds, 0, -1):
        await ctx.send(str(i))
        await asyncio.sleep(1)
    await ctx.send("Go!")

@client.command(help="Sends a random emoji.")
async def randomemoji(ctx):
    emojis = ["😄", "🔥", "🚀", "🎉", "🤖", "👾"] # ----- I plan on adding more soon -----
    await ctx.send(random.choice(emojis))

@client.command(help="Creates a mosaic of random emojis.")
async def emojiart(ctx, rows: int = 5, cols: int = 10):
    emojis = ["😄", "🔥", "🚀", "🎉", "🤖", "👾"] # ----- I plan on adding more soon -----
    art = "\n".join("".join(random.choice(emojis) for _ in range(cols)) for _ in range(rows))
    await ctx.send(art)

@client.command(help="Turns text into ASCII art using pyfiglet.")
async def asciiarttext(ctx, *, text: str):
    try:
        import pyfiglet
    except ImportError:
        return await ctx.send("pyfiglet module not installed.")
    art = pyfiglet.figlet_format(text)
    if len(art) > 2000:
        await ctx.send("Output too long.")
    else:
        await ctx.send(f"```\n{art}\n```")

@client.command(help="Flips your text upside-down.")
async def fliptext(ctx, *, text: str):
    mapping = str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", 
                             "ɐqɔpǝɟƃɥᴉɾʞʅɯuodbɹsʇnʌʍxʎz∀𐐒ƆᗡƎℲ⅁HIſʞ⅂WNOԀQᴚS⊥∩ΛMX⅄Z")
    flipped = text[::-1].translate(mapping)
    await ctx.send(flipped)

@client.command(help="Shuffles the digits of the current time.")
async def shuffletime(ctx):
    now = datetime.utcnow().strftime("%H:%M:%S")
    digits = list(now.replace(":", ""))
    random.shuffle(digits)
    shuffled = "".join(digits)
    await ctx.send(f"Original time: {now} | Shuffled: {shuffled}")

@client.command(help="Repeats text multiple times with increasing delay.")
async def hypertext(ctx, repeats: int, *, text: str):
    for i in range(1, repeats + 1):
        await ctx.send(text)
        await asyncio.sleep(0.1 * i)

@client.command(help="Simulates a crash with a fake error message.")
async def simulatecrash(ctx):
    await ctx.send("Oh no! An unexpected error occurred! [SIMULATED CRASH]")
    await asyncio.sleep(1)
    await ctx.send("Restarting self...")

@client.command(help="Sends a message that is then quickly deleted.")
async def invisibility(ctx, *, text: str):
    message = await ctx.send(text)
    await asyncio.sleep(0.5)
    await message.delete()

@client.command(help="Tells you what time it will be after a number of seconds.")
async def timeshift(ctx, seconds: int):
    future_time = datetime.utcnow() + timedelta(seconds=seconds)
    await ctx.send(f"In {seconds} seconds, it will be {future_time.strftime('%H:%M:%S')} UTC.")

@client.command(help="Outputs your text along with its mirror image.")
async def mirror(ctx, *, text: str):
    await ctx.send(f"{text}\n{text[::-1]}")

@client.command(help="Sends 'Beep!' a number of times.")
async def beep(ctx, count: int = 5):
    for _ in range(count):
        await ctx.send("Beep!")
        await asyncio.sleep(0.5)

@client.command(help="Edits one of your messages to show a live countdown.")
async def countdownedit(ctx, msg_id: int, seconds: int):
    try:
        message = await ctx.channel.fetch_message(msg_id)
        if message.author.id != ctx.author.id:
            return await ctx.send("You can only edit your own messages.")
        for i in range(seconds, 0, -1):
            await message.edit(content=f"Editing in {i} seconds...")
            await asyncio.sleep(1)
        await message.edit(content="Countdown complete!")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@client.command(help="Randomizes the case of your text.")
async def randomcase(ctx, *, text: str):
    new_text = "".join(random.choice([c.upper(), c.lower()]) for c in text)
    await ctx.send(new_text)

@client.command(help="Repeats each character in your text.")
async def doubletext(ctx, *, text: str):
    doubled = "".join(c*2 for c in text)
    await ctx.send(doubled)

@client.command(help="Inserts spaces between each character.")
async def breaktext(ctx, *, text: str):
    spaced = " ".join(list(text))
    await ctx.send(spaced)

@client.command(help="Splits each word into letters on separate lines.")
async def wordsplit(ctx, *, text: str):
    splitted = "\n".join(" ".join(list(word)) for word in text.split())
    await ctx.send(splitted)

@client.command(help="Reverses the order of words in your text.")
async def reverseorder(ctx, *, text: str):
    reversed_order = " ".join(text.split()[::-1])
    await ctx.send(reversed_order)

@client.command(help="Obscures your text by inserting zero-width characters.")
async def secretmessage(ctx, *, text: str):
    secret = "\u200b".join(text)
    await ctx.send(f"Secret: {secret}")

@client.command(help="Adds random ANSI color flair to your text (in code block).")
async def colorize(ctx, *, text: str):
    colors = ['\033[91m', '\033[92m', '\033[93m', '\033[94m']
    colored = "".join(random.choice(colors) + char for char in text) + "\033[0m"
    await ctx.send(f"```ansi\n{colored}\n```")

@client.command(help="Sends a random fun fact.")
async def randomfact(ctx):
    facts = [
        "Honey never spoils.",
        "A bolt of lightning contains enough energy to toast 100,000 slices of bread.",
        "Bananas are berries but strawberries are not.",
        "Octopuses have three hearts.",
        "There are more stars in the universe than grains of sand on Earth."
        # ----- I plan on adding more soon 😂 -----
    ]
    await ctx.send(random.choice(facts))
    
@client.command(help="Ask ai model deepseek a question.")
async def deepseek(ctx, *, question):
    reply = query_groq("deepseek-r1-distill-qwen-32b", question)
    response = "**AI Response: **" + reply 
    await send_long_message(ctx, response)

@client.command(help="Ask ai model llama a question.")
async def llama(ctx, *, question):
    reply = query_groq("llama-3.3-70b-versatile", question)
    response = "**AI Response: **" + reply 
    await send_long_message(ctx, response)

@client.command(help="Ask ai model gemma a question.")
async def gemma(ctx, *, question):
    reply = query_groq("gemma2-9b-it", question)
    response = "**AI Response: **" + reply 
    await send_long_message(ctx, response)

@client.command(help="Ask ai model gemma a question.")
async def meta_ai(ctx, *, question):
    reply = query_groq("llama-3.1-8b-instant", question)
    response = "**AI Response: **" + reply 
    await send_long_message(ctx, response)
    
@client.command(help="Repeats your message a specified number of times with a delay.")
async def repeat(ctx, times: int, delay: int, *, message: str):
    global running
    if not running:
        await ctx.send("Command execution is currently stopped.")
        return

    for i in range(1, times + 1):
        if not running:
            await ctx.send("Command execution has been stopped midway.")
            break
        await ctx.send(f"{message} ({i})")
        await asyncio.sleep(delay)

@client.command(help="Stops all running commands.")
async def stopcommands(ctx):
    global running
    running = False
    await ctx.send("Commands have been stopped.")

@client.command(help="Resumes command execution.")
async def startcommands(ctx):
    global running
    running = True
    await ctx.send("Commands have been resumed. You can now run more commands.")
    
@client.command(help="Diddy replies for you. Use as reply or provide message ID.")
async def diddy(ctx, message_id: int = None):
    ref_msg = None

    if ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(
            ctx.message.reference.message_id
        )

    elif message_id:
        async for msg in ctx.channel.history(limit=100):
            if msg.id == message_id:
                ref_msg = msg
                break

        if ref_msg is None:
            await ctx.send(
                "That message ID isn’t in this channel or is too old, baby."
            )
            return

    else:
        await ctx.send(
            "You gotta reply to a message or give me the message ID, baby."
        )
        return

    target_user = ref_msg.author
    target_content = ref_msg.content

    async with ctx.typing():
        await asyncio.sleep(random.uniform(1.0, 2.5))

        prompt_styles = [
            "You are a parody of P Diddy. Respond like you're about to massage someone with warm baby oil and quote 90s R&B lines.",
            "You're dirty Diddy. You make people feel deeply uncomfortable with slow, intimate, unsettling compliments.",
            "You're absurd, sensual, and chaotic. Whisper nonsense like 'you smell like cocoa butter dreams'."
        ]

        prompt = (
            f"{random.choice(prompt_styles)}\n"
            f'The user said: "{target_content}"\n'
            "Respond to them in character. Keep your response short."
        )

        # Llama through Groq
        reply = query_groq("qwen/qwen3.8-27b", prompt)

        response = (
            f"**Diddy whispers to {target_user.mention}:** {reply}"
        )

    await ref_msg.reply(response)

    try:
        await ref_msg.add_reaction("🧴")
    except Exception:
        pass
        
@client.command(help="Spams Extremely fast. (Warning cam cause rate limiting at high amounts)")
async def fastspam(ctx, number: int, *, message: str):
    for _ in range(number):
        await ctx.send(message)

        
# ----- Here it runs your token as a selfbot -----
client.run(token, bot=False)
