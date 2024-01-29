import discord
import config
from discord.ext import tasks, commands
from valve.source.a2s import ServerQuerier
from valve import rcon as rcon
from datetime import datetime
from config import TOKEN, server_channels, guild_id, log_channel_id

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

created_channels = {}


@bot.event
async def on_ready():
    log_channel = bot.get_channel(log_channel_id)
    print(f'Вошел как {bot.user.name}')
    await log_channel.send(f'[SPAM] Бот запущен: {datetime.utcnow()}')
    update_channel.start()


@tasks.loop(minutes=1)
async def update_channel():
    try:
        log_channel = bot.get_channel(log_channel_id)
        for server_address, server_info in server_channels.items():
            ip, port = server_address.split(':')
            server_querier = ServerQuerier((ip, int(port)))
            info = server_querier.info()

            players_online = info["player_count"]
            max_players = info["max_players"]
            server_name = server_info['name']

            if server_name in created_channels:
                old_channel = created_channels[server_name]
                await old_channel.delete()

            channel_name = f'{server_name} - {players_online}/{max_players}'

            guild = bot.get_guild(guild_id)

            new_channel = await guild.create_voice_channel(channel_name)
            created_channels[server_name] = new_channel
            await log_channel.send(
                f'[SPAM] Создан новый голосовой канал для сервера {server_name}: {channel_name} в {datetime.utcnow()}')

    except Exception as e:
        print(f'Ошибка при создании/удалении голосового канала: {e}')
        await log_channel.send(f'Ошибка при создании/удалении голосового канала: {e}')


@bot.event
async def on_command_error(ctx, error):
    log_channel = bot.get_channel(log_channel_id)
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Неизвестная команда. Введите `!!help` для списка доступных команд.")
        await log_channel.send(f'Получена неизвестная команда: {ctx.message.content}')


@update_channel.before_loop
async def before_update_channel():
    await bot.wait_until_ready()


@bot.command()
async def players(ctx):
    for server_address, server_info in server_channels.items():
        ip, port = server_address.split(':')
        server_querier = ServerQuerier((ip, int(port)))
        info = server_querier.info()
        players = server_querier.players()
        player_list = "\n".join([f"{player['name']}" for player in players['players']])
        await ctx.send(f"Игроки на сервере {server_info['name']}:\n{player_list}")


@bot.command()
async def kick(ctx, *, player_name):
    for server_address, server_info in server_channels.items():
        server_name = server_info['name']
        await ctx.send(f"Пытаюсь кикнуть игрока {player_name} с сервера {server_name} {server_address}...")
        try:
            ip, port = server_address.split(':')  # Разделение IP-адреса и порта
            with rcon.RCON((ip, int(port)), config.rcon_password) as rcon_connection:
                rcon_connection.execute(f"kick {player_name}")
                await ctx.send(f"Игрок {player_name} кикнут с сервера {server_name}")

                # Отправка лога в лог-канал
                log_channel = bot.get_channel(config.log_channel_id)
                await log_channel.send(
                    f"[KICK] Пользователь {ctx.author} использовал команду kick для кика игрока {player_name} с сервера {server_name}")
        except Exception as e:
            await ctx.send(f"Произошла ошибка при попытке кикнуть игрока {player_name} с сервера {server_name}: {e}")


bot.run(TOKEN)
