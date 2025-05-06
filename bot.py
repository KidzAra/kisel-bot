import disnake
from disnake.ext import commands
import json
import os
import time
import random
from typing import List, Dict, Any, Optional
from config import TOKEN, DATA_FILE, SCORE_FILE

# Попытка импорта ID серверов из config.py
try:
    from config import GUILD_IDS
except ImportError:
    GUILD_IDS = []  # Если не определены, используем пустой список

# Инициализация бота с синхронизацией команд
intents = disnake.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True  # Для получения информации о статусах пользователей

# Использование CommandSyncFlags вместо устаревших параметров
command_sync_flags = commands.CommandSyncFlags.default()
command_sync_flags.sync_commands = True
command_sync_flags.sync_commands_debug = True

bot = commands.Bot(
    command_prefix="/", 
    intents=intents,
    command_sync_flags=command_sync_flags
)

# Управление данными о друзьях
def load_friend_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_friend_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Управление данными о счетах пользователей
def load_score_data():
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_score_data(data):
    with open(SCORE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Обработчики событий
# Словарь для отслеживания времени в голосовых каналах. Ключ - ID пользователя, значение - время входа
voice_time_tracker = {}

@bot.event
async def on_ready():
    print(f"==========================================")
    print(f"Бот {bot.user} успешно подключен к Discord!")
    print(f"ID бота: {bot.user.id}")
    print(f"Количество серверов: {len(bot.guilds)}")
    for guild in bot.guilds:
        print(f"- {guild.name} (ID: {guild.id})")
    print(f"==========================================")
    print(f"Используйте Ctrl+C для остановки бота")
    
    # Установка статуса бота
    await bot.change_presence(
        activity=disnake.Activity(
            type=disnake.ActivityType.listening,
            name="/friendhelp"
        )
    )

@bot.event
async def on_voice_state_update(member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
    """Обработчик события изменения состояния голосового канала"""
    user_id = str(member.id)
    
    # Пользователь вошел в голосовой канал
    if before.channel is None and after.channel is not None:
        voice_time_tracker[user_id] = time.time()
    
    # Пользователь вышел из голосового канала
    elif before.channel is not None and (after.channel is None or after.channel != before.channel):
        if user_id in voice_time_tracker:
            enter_time = voice_time_tracker[user_id]
            current_time = time.time()
            minutes_in_voice = int((current_time - enter_time) // 60)  # Получаем количество минут
            
            if minutes_in_voice > 0:
                # Загружаем данные о счетах
                scores = load_score_data()
                
                # Обновляем счет пользователя
                if user_id not in scores:
                    scores[user_id] = 0
                
                scores[user_id] += minutes_in_voice
                
                # Сохраняем данные
                save_score_data(scores)
                
                print(f"Пользователь {member.name} (ID: {user_id}) получил {minutes_in_voice} очков за {minutes_in_voice} минут в голосовом канале")
            
            # Удаляем запись о времени входа
            del voice_time_tracker[user_id]
    
    # Если пользователь сменил канал, обновляем время входа
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        voice_time_tracker[user_id] = time.time()

# Группа команд для управления друзьями
class FriendCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.friend_data = load_friend_data()
    
    def get_user_friends(self, user_id: str) -> List[str]:
        """Получить список друзей пользователя"""
        return self.friend_data.get(str(user_id), [])
    
    @commands.slash_command(
        name="friendhelp",
        description="Показывает информацию о командах для управления друзьями",
        guild_ids=GUILD_IDS
    )
    async def friendhelp(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title="Помощь по командам управления друзьями",
            color=disnake.Color.blue()
        )
        
        embed.add_field(
            name="/friendhelp",
            value="Показывает это сообщение с помощью",
            inline=False
        )
        
        embed.add_field(
            name="/addfriend [пользователь]",
            value="Добавляет указанного пользователя в ваш список друзей",
            inline=False
        )
        
        embed.add_field(
            name="/removefriend [пользователь]",
            value="Удаляет указанного пользователя из вашего списка друзей",
            inline=False
        )
        
        embed.add_field(
            name="/friendlist",
            value="Показывает ваш список друзей",
            inline=False
        )
        
        embed.add_field(
            name="/callvoice",
            value="Отправляет уведомление о голосовом вызове всем вашим друзьям",
            inline=False
        )
        
        embed.add_field(
            name="/whoisplaying",
            value="Показывает, во что играют ваши друзья, сгруппированные по играм",
            inline=False
        )
        
        await inter.response.send_message(embed=embed, ephemeral=True)
    
    @commands.slash_command(
        name="addfriend",
        description="Добавить пользователя в список друзей",
        guild_ids=GUILD_IDS
    )
    async def addfriend(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(description="Пользователь для добавления в список друзей")
    ):
        user_id = str(inter.author.id)
        friend_id = str(user.id)
        
        # Инициализация списка друзей пользователя, если он не существует
        if user_id not in self.friend_data:
            self.friend_data[user_id] = []
        
        # Проверка, есть ли пользователь уже в списке друзей
        if friend_id in self.friend_data[user_id]:
            await inter.response.send_message(f"{user.mention} уже находится в вашем списке друзей.", ephemeral=True)
            return
        
        # Добавление пользователя в список друзей
        self.friend_data[user_id].append(friend_id)
        save_friend_data(self.friend_data)
        
        await inter.response.send_message(f"{user.mention} добавлен в ваш список друзей.", ephemeral=True)
    
    @commands.slash_command(
        name="removefriend",
        description="Удалить пользователя из списка друзей",
        guild_ids=GUILD_IDS
    )
    async def removefriend(self, inter: disnake.ApplicationCommandInteraction):
        user_id = str(inter.author.id)
        
        # Получение списка друзей пользователя
        if user_id not in self.friend_data or not self.friend_data[user_id]:
            await inter.response.send_message("Ваш список друзей пуст.", ephemeral=True)
            return
        
        # Создание опций для выпадающего меню
        options = []
        for friend_id in self.friend_data[user_id]:
            try:
                friend = await bot.fetch_user(int(friend_id))
                options.append(disnake.SelectOption(
                    label=f"{friend.name}",
                    value=friend_id,
                    description=f"Удалить {friend.name} из вашего списка друзей"
                ))
            except:
                # Пользователь не найден, удаляем из списка
                self.friend_data[user_id].remove(friend_id)
                save_friend_data(self.friend_data)
                continue
        
        # Создание выпадающего меню
        select = disnake.ui.Select(
            placeholder="Выберите друга для удаления",
            options=options,
            custom_id="remove_friend_select"
        )
        
        # Создание представления и добавление выпадающего меню
        view = disnake.ui.View()
        view.add_item(select)
        
        await inter.response.send_message("Выберите друга для удаления:", view=view, ephemeral=True)
    
    # Корректная обработка взаимодействия с выпадающим меню для disnake
    @commands.Cog.listener("on_dropdown")
    async def on_friend_remove_dropdown(self, inter: disnake.MessageInteraction):
        # Проверка, что это наше выпадающее меню
        if inter.component.custom_id == "remove_friend_select":
            user_id = str(inter.author.id)
            friend_id = inter.values[0]
            
            # Удаление пользователя из списка друзей
            if user_id in self.friend_data and friend_id in self.friend_data[user_id]:
                self.friend_data[user_id].remove(friend_id)
                save_friend_data(self.friend_data)
                
                try:
                    friend = await bot.fetch_user(int(friend_id))
                    await inter.response.send_message(f"{friend.mention} удален из вашего списка друзей.", ephemeral=True)
                except:
                    await inter.response.send_message("Пользователь удален из вашего списка друзей.", ephemeral=True)
            else:
                await inter.response.send_message("Пользователь не найден в вашем списке друзей.", ephemeral=True)

    # Общий обработчик взаимодействий с компонентами интерфейса
    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        # Обрабатываем различные кнопки по их custom_id
        if inter.component.custom_id.startswith("voice_"):
            await inter.response.send_message("Перенаправление в голосовой канал...", ephemeral=True)
    
    @commands.slash_command(
        name="friendlist",
        description="Показать список друзей",
        guild_ids=GUILD_IDS
    )
    async def friendlist(self, inter: disnake.ApplicationCommandInteraction):
        user_id = str(inter.author.id)
        
        # Получение списка друзей пользователя
        if user_id not in self.friend_data or not self.friend_data[user_id]:
            await inter.response.send_message("Ваш список друзей пуст.", ephemeral=True)
            return
        
        # Создание встраиваемого сообщения
        embed = disnake.Embed(
            title="Ваш список друзей",
            color=disnake.Color.green()
        )
        
        # Добавление друзей во встраиваемое сообщение
        for i, friend_id in enumerate(self.friend_data[user_id], 1):
            try:
                friend = await bot.fetch_user(int(friend_id))
                embed.add_field(
                    name=f"{i}. {friend.name}",
                    value=f"ID: {friend.id}",
                    inline=False
                )
            except:
                embed.add_field(
                    name=f"{i}. Неизвестный пользователь",
                    value=f"ID: {friend_id} (Пользователь не найден)",
                    inline=False
                )
        
        await inter.response.send_message(embed=embed, ephemeral=True)
    
    @commands.slash_command(
        name="callvoice",
        description="Отправить уведомление о голосовом вызове всем друзьям",
        guild_ids=GUILD_IDS
    )
    async def callvoice(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        режим: str = commands.Param(
            description="Режим оповещения: всем друзьям или только онлайн",
            choices=["Онлайн", "Все"],
            default="Онлайн"
        )
    ):
        user_id = str(inter.author.id)
        
        # Получение списка друзей пользователя
        if user_id not in self.friend_data or not self.friend_data[user_id]:
            await inter.response.send_message("Ваш список друзей пуст.", ephemeral=True)
            return
        
        # Создание уведомления
        embed = disnake.Embed(
            title="Кто-то зовет тебя в войс!",
            description=f"{inter.author.mention}, зовет вас в войс!",
            color=disnake.Color.purple()
        )
        
        # Установка текста нижнего колонтитула - пояснительный текст из изображения
        embed.set_footer(text="Если ты видишь это сообщение значит пользователь добавил тебя в список друзей, теперь он может вызывать всех своих друзей в войс одной командой. Что бы тоже использовать эту функцию используй команду /friendhelp")
        
        # Добавление изображения напитка справа, как показано в примере
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1341271551483314230/1360642059408642048/7sQDreU.png?ex=67fbdc2a&is=67fa8aaa&hm=b128533f075bc0293e715c2ee38e723ed58e9fe3e456ad92def6e3113bfac18b&=&width=1024&height=1024")  # Предоставленное изображение напитка
        
        # Проверка, находится ли пользователь в голосовом канале
        voice_channel = None
        if inter.author.voice:
            voice_channel = inter.author.voice.channel
        
        # Отправка уведомлений друзьям в зависимости от выбранного режима
        sent_count = 0
        skipped_count = 0
        
        await inter.response.defer(ephemeral=True)
        
        # Предварительная проверка статусов всех пользователей для отладки
        status_info = []
        if режим == "Онлайн":
            for guild in bot.guilds:
                status_info.append(f"Сервер: {guild.name} (ID: {guild.id})")
                for friend_id in self.friend_data[user_id]:
                    try:
                        member = guild.get_member(int(friend_id))
                        if member:
                            friend_name = member.name
                            status_info.append(f"  - {friend_name} (ID: {friend_id}): {member.status}")
                    except Exception as e:
                        status_info.append(f"  - Ошибка получения информации о пользователе {friend_id}: {e}")
        
        for friend_id in self.friend_data[user_id]:
            try:
                friend = await bot.fetch_user(int(friend_id))
                
                # Проверка статуса пользователя, если выбран режим "Онлайн"
                if режим == "Онлайн":
                    # Получаем объект участника на общих серверах
                    online_status = False
                    status_debug = "не найден на общих серверах"
                    
                    # Проверяем все общие серверы с пользователем
                    for guild in bot.guilds:
                        member = guild.get_member(int(friend_id))
                        if member:
                            # Вывод отладочной информации
                            print(f"Проверка статуса {friend.name} (ID: {friend_id}) на сервере {guild.name}: {member.status}")
                            
                            # Проверяем статус: в сети, неактивен, не беспокоить или стримит
                            if member.status == disnake.Status.online or member.status == disnake.Status.idle or member.status == disnake.Status.dnd or member.status == disnake.Status.streaming:
                                online_status = True
                                status_debug = f"в сети на сервере {guild.name} со статусом {member.status}"
                                break
                    
                    # Если пользователь не онлайн, пропускаем его
                    if not online_status:
                        print(f"Пропускаем {friend.name} (ID: {friend_id}): {status_debug}")
                        skipped_count += 1
                        continue
                    else:
                        print(f"Отправляем сообщение {friend.name} (ID: {friend_id}): {status_debug}")
                
                # Создание представления с кнопкой голосового канала, если пользователь находится в голосовом канале
                view = None
                if voice_channel:
                    view = disnake.ui.View()
                    voice_button = disnake.ui.Button(
                        style=disnake.ButtonStyle.primary,
                        label="Войс",
                        emoji="🎤",
                        url=f"https://discord.com/channels/{inter.guild.id}/{voice_channel.id}"
                    )
                    view.add_item(voice_button)
                
                # Отправка личного сообщения другу
                await friend.send(embed=embed, view=view)
                sent_count += 1
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {friend_id}: {e}")
                continue
        
        # Отправка результата
        if режим == "Онлайн":
            result_message = f"Уведомление о голосовом вызове отправлено {sent_count} друзьям, которые сейчас онлайн. {skipped_count} пользователей пропущено (не в сети)."
            
            # Добавляем отладочную информацию, если есть проблемы
            if sent_count == 0 and skipped_count > 0:
                # Ограничиваем количество строк в сообщении, чтобы не превысить лимит
                debug_info = "\n\nОтладочная информация о статусах (до 15 строк):\n" + "\n".join(status_info[:15])
                if len(status_info) > 15:
                    debug_info += f"\n...и еще {len(status_info) - 15} строк"
                
                result_message += debug_info
            
            await inter.edit_original_message(content=result_message)
        else:
            await inter.edit_original_message(content=f"Уведомление о голосовом вызове отправлено {sent_count} друзьям (всем в списке).")

    @commands.slash_command(
        name="whoisplaying",
        description="Показывает, во что играют ваши друзья, сгруппированные по играм",
        guild_ids=GUILD_IDS
    )
    async def whoisplaying(self, inter: disnake.ApplicationCommandInteraction):
        user_id = str(inter.author.id)
        
        # Получение списка друзей пользователя
        if user_id not in self.friend_data or not self.friend_data[user_id]:
            await inter.response.send_message("Ваш список друзей пуст.", ephemeral=True)
            return
        
        await inter.response.defer(ephemeral=True)
        
        # Создаем словарь с играми и кто в них играет
        # Ключ - название игры, значение - список друзей
        games_dict = {}
        online_friends = []  # Друзья в сети, но не играющие
        offline_friends = []  # Друзья не в сети
        
        # Проходим по всем друзьям из списка
        for friend_id in self.friend_data[user_id]:
            try:
                friend_user = await bot.fetch_user(int(friend_id))
                friend_name = friend_user.name
                friend_avatar = friend_user.display_avatar.url
                
                # Флаг, чтобы отслеживать, найден ли пользователь хотя бы на одном сервере
                found_on_server = False
                playing_game = False
                
                # Проверяем статус друга на всех серверах, где есть бот
                for guild in bot.guilds:
                    member = guild.get_member(int(friend_id))
                    if member:
                        found_on_server = True
                        
                        # Проверяем, в сети ли пользователь
                        if member.status != disnake.Status.offline:
                            # Проверяем, играет ли пользователь в игру
                            if member.activity and (member.activity.type == disnake.ActivityType.playing or member.activity.type == disnake.ActivityType.streaming):
                                game_name = member.activity.name
                                playing_game = True
                                
                                # Добавляем игру и друга в словарь
                                if game_name not in games_dict:
                                    games_dict[game_name] = []
                                
                                games_dict[game_name].append({
                                    "name": friend_name,
                                    "id": friend_id,
                                    "avatar": friend_avatar,
                                    "status": str(member.status),
                                    "activity_details": member.activity.details if hasattr(member.activity, "details") and member.activity.details else None
                                })
                                
                                # Останавливаем цикл после нахождения играющего друга
                                break
                            else:
                                # Если друг в сети, но не играет, добавляем в список онлайн
                                online_friends.append({
                                    "name": friend_name,
                                    "id": friend_id,
                                    "avatar": friend_avatar,
                                    "status": str(member.status)
                                })
                                # Останавливаем цикл после нахождения друга в сети
                                break
                
                # Если пользователь найден на сервере, но не играет и не в онлайн-списке
                if found_on_server and not playing_game and not any(f["id"] == friend_id for f in online_friends):
                    # Добавляем в список оффлайн
                    offline_friends.append({
                        "name": friend_name,
                        "id": friend_id,
                        "avatar": friend_avatar
                    })
                
                # Если пользователь не найден ни на одном сервере
                if not found_on_server:
                    offline_friends.append({
                        "name": friend_name,
                        "id": friend_id,
                        "avatar": friend_avatar
                    })
                
            except Exception as e:
                print(f"Ошибка при получении информации о пользователе {friend_id}: {e}")
                continue
        
        # Создаем эмбед с результатами
        embed = disnake.Embed(
            title="Во что играют ваши друзья",
            color=disnake.Color.blurple(),
            description=f"Всего друзей: {len(self.friend_data[user_id])}" if self.friend_data[user_id] else "У вас нет друзей в списке."
        )
        
        # Добавляем поля для каждой игры
        if games_dict:
            for game_name, players in games_dict.items():
                # Формируем список игроков для данной игры
                players_text = ""
                for player in players:
                    status_emoji = "🟢" if player["status"] == "online" else "🟡" if player["status"] == "idle" else "🔴" if player["status"] == "dnd" else "🟣" if player["status"] == "streaming" else "⚪"
                    details = f" • {player['activity_details']}" if player["activity_details"] else ""
                    players_text += f"{status_emoji} {player['name']}{details}\n"
                
                # Добавляем поле с названием игры и списком игроков
                embed.add_field(
                    name=f"🎮 {game_name} ({len(players)})",
                    value=players_text,
                    inline=False
                )
        else:
            embed.add_field(
                name="🎮 Никто не играет",
                value="В данный момент никто из ваших друзей не играет.",
                inline=False
            )
        
        # Добавляем поле с друзьями в сети, но не играющими
        if online_friends:
            online_text = ""
            for friend in online_friends:
                status_emoji = "🟢" if friend["status"] == "online" else "🟡" if friend["status"] == "idle" else "🔴" if friend["status"] == "dnd" else "🟣" if friend["status"] == "streaming" else "⚪"
                online_text += f"{status_emoji} {friend['name']}\n"
            
            embed.add_field(
                name=f"💻 В сети ({len(online_friends)})",
                value=online_text,
                inline=False
            )
        
        # Добавляем поле с оффлайн друзьями (опциональное, можно ограничить)
        if offline_friends and len(offline_friends) <= 10:  # Ограничиваем для компактности
            offline_text = ""
            for friend in offline_friends:
                offline_text += f"⚫ {friend['name']}\n"
            
            embed.add_field(
                name=f"💤 Не в сети ({len(offline_friends)})",
                value=offline_text,
                inline=False
            )
        elif offline_friends:
            embed.add_field(
                name=f"💤 Не в сети ({len(offline_friends)})",
                value=f"Всего не в сети: {len(offline_friends)} друзей",
                inline=False
            )
        
        # Устанавливаем время обновления
        embed.set_footer(text=f"Обновлено: {disnake.utils.utcnow().strftime('%d.%m.%Y %H:%M:%S')} UTC")
        
        # Отправляем эмбед
        await inter.edit_original_message(embed=embed)

# Группа команд для управления счетами и магазином
class ScoreCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.score_data = load_score_data()
        # Словарь для отслеживания покупок пользователей
        self.purchases = {}
    
    def get_user_score(self, user_id: str) -> int:
        """Получить счет пользователя"""
        return self.score_data.get(str(user_id), 0)
    
    def has_made_purchase(self, user_id: str, purchase_type: str) -> bool:
        """Проверить, совершил ли пользователь определенную покупку"""
        if str(user_id) not in self.purchases:
            return False
        return purchase_type in self.purchases[str(user_id)]
    
    def add_purchase(self, user_id: str, purchase_type: str) -> None:
        """Добавить запись о покупке пользователя"""
        if str(user_id) not in self.purchases:
            self.purchases[str(user_id)] = []
        
        if purchase_type not in self.purchases[str(user_id)]:
            self.purchases[str(user_id)].append(purchase_type)
    
    @commands.slash_command(
        name="score",
        description="Показать ваш текущий счет",
        guild_ids=GUILD_IDS
    )
    async def score(self, inter: disnake.ApplicationCommandInteraction):
        """Команда для просмотра своего счета"""
        user_id = str(inter.author.id)
        user_score = self.get_user_score(user_id)
        
        embed = disnake.Embed(
            title="Ваш счет",
            description=f"У вас {user_score} очков",
            color=disnake.Color.green()
        )
        
        await inter.response.send_message(embed=embed, ephemeral=True)
    
    @commands.slash_command(
        name="addscore",
        description="Добавить очки пользователю (только для администраторов)",
        guild_ids=GUILD_IDS
    )
    @commands.has_permissions(administrator=True)
    async def addscore(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member = commands.Param(description="Пользователь, которому нужно добавить очки"),
        количество: int = commands.Param(description="Количество очков для добавления", gt=0)
    ):
        """Команда для добавления очков пользователю"""
        user_id = str(участник.id)
        
        # Обновляем счет пользователя
        if user_id not in self.score_data:
            self.score_data[user_id] = 0
        
        self.score_data[user_id] += количество
        save_score_data(self.score_data)
        
        embed = disnake.Embed(
            title="Очки добавлены",
            description=f"Пользователю {участник.mention} добавлено {количество} очков.\nТекущий счет: {self.score_data[user_id]}",
            color=disnake.Color.green()
        )
        
        await inter.response.send_message(embed=embed, ephemeral=True)
    
    @commands.slash_command(
        name="removescore",
        description="Удалить очки у пользователя (только для администраторов)",
        guild_ids=GUILD_IDS
    )
    @commands.has_permissions(administrator=True)
    async def removescore(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member = commands.Param(description="Пользователь, у которого нужно убрать очки"),
        количество: int = commands.Param(description="Количество очков для удаления", gt=0)
    ):
        """Команда для удаления очков у пользователя"""
        user_id = str(участник.id)
        
        # Проверяем наличие пользователя в данных
        if user_id not in self.score_data:
            self.score_data[user_id] = 0
        
        # Проверяем, чтобы счет не стал отрицательным
        if self.score_data[user_id] < количество:
            self.score_data[user_id] = 0
        else:
            self.score_data[user_id] -= количество
        
        save_score_data(self.score_data)
        
        embed = disnake.Embed(
            title="Очки удалены",
            description=f"У пользователя {участник.mention} удалено {количество} очков.\nТекущий счет: {self.score_data[user_id]}",
            color=disnake.Color.red()
        )
        
        await inter.response.send_message(embed=embed, ephemeral=True)
    
    @commands.slash_command(
        name="shop",
        description="Открыть магазин товаров",
        guild_ids=GUILD_IDS
    )
    async def shop(self, inter: disnake.ApplicationCommandInteraction):
        """Команда для открытия магазина товаров"""
        user_id = str(inter.author.id)
        user_score = self.get_user_score(user_id)
        
        # Создаем встраиваемое сообщение для магазина
        embed = disnake.Embed(
            title="Магазин товаров",
            description=f"Ваш текущий счет: {user_score}",
            color=disnake.Color.blue()
        )
        
        # Добавляем информацию о доступных товарах
        embed.add_field(
            name="Повышение (10000 очков)",
            value="Заменяет роль на более высокую\nПрименяется единоразово",
            inline=False
        )
        
        embed.add_field(
            name="Кастомная роль (2500 очков)",
            value="Создает свою собственную кастомную роль с выбранным названием и цветом\nПрименяется единоразово",
            inline=False
        )
        
        # Создаем кнопки для покупки
        view = disnake.ui.View()
        
        # Кнопка для покупки повышения
        promotion_button = disnake.ui.Button(
            style=disnake.ButtonStyle.primary,
            label="Купить повышение",
            custom_id="buy_promotion",
            disabled=user_score < 10000 or self.has_made_purchase(user_id, "promotion")
        )
        view.add_item(promotion_button)
        
        # Кнопка для покупки кастомной роли
        custom_role_button = disnake.ui.Button(
            style=disnake.ButtonStyle.success,
            label="Купить кастомную роль",
            custom_id="buy_custom_role",
            disabled=user_score < 2500 or self.has_made_purchase(user_id, "custom_role")
        )
        view.add_item(custom_role_button)
        
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @commands.Cog.listener("on_button_click")
    async def on_shop_button_click(self, inter: disnake.MessageInteraction):
        """Обработчик нажатия на кнопки магазина"""
        user_id = str(inter.author.id)
        
        # Проверяем, что это кнопка из магазина
        if inter.component.custom_id == "buy_promotion":
            # Покупка повышения
            if self.get_user_score(user_id) < 10000:
                await inter.response.send_message("У вас недостаточно очков для этой покупки!", ephemeral=True)
                return
            
            if self.has_made_purchase(user_id, "promotion"):
                await inter.response.send_message("Вы уже приобрели это повышение!", ephemeral=True)
                return
            
            # Получаем участника на сервере
            member = inter.guild.get_member(int(user_id))
            if not member:
                await inter.response.send_message("Не удалось получить информацию о вашем профиле на сервере", ephemeral=True)
                return
            
            # Ищем роли для замены
            old_role = inter.guild.get_role(1341275045502259230)
            new_role = inter.guild.get_role(1341273303880437760)
            
            if not old_role or not new_role:
                await inter.response.send_message("Не удалось найти необходимые роли. Обратитесь к администратору.", ephemeral=True)
                return
            
            # Проверяем, есть ли у пользователя роль, которую нужно заменить
            if old_role not in member.roles:
                await inter.response.send_message("У вас нет роли, которую можно повысить!", ephemeral=True)
                return
            
            try:
                # Удаляем старую роль и добавляем новую
                await member.remove_roles(old_role)
                await member.add_roles(new_role)
                
                # Списываем очки
                self.score_data[user_id] -= 10000
                save_score_data(self.score_data)
                
                # Записываем покупку
                self.add_purchase(user_id, "promotion")
                
                await inter.response.send_message(f"Поздравляем! Вы успешно приобрели повышение роли. С вашего счета списано 10000 очков.", ephemeral=True)
            except Exception as e:
                print(f"Ошибка при изменении ролей: {e}")
                await inter.response.send_message("Произошла ошибка при изменении ролей. Обратитесь к администратору.", ephemeral=True)
        
        elif inter.component.custom_id == "buy_custom_role":
            # Покупка кастомной роли
            if self.get_user_score(user_id) < 2500:
                await inter.response.send_message("У вас недостаточно очков для этой покупки!", ephemeral=True)
                return
            
            if self.has_made_purchase(user_id, "custom_role"):
                await inter.response.send_message("Вы уже приобрели кастомную роль!", ephemeral=True)
                return
            
            # Создаем модальное окно для ввода данных о роли
            modal = disnake.ui.Modal(
                title="Создание кастомной роли",
                custom_id="custom_role_modal",
                components=[
                    disnake.ui.TextInput(
                        label="Название роли",
                        placeholder="Введите название для вашей роли",
                        custom_id="role_name",
                        style=disnake.TextInputStyle.short,
                        max_length=32
                    ),
                    disnake.ui.TextInput(
                        label="HEX код цвета (опционально)",
                        placeholder="Например: #FF5733",
                        custom_id="role_color",
                        style=disnake.TextInputStyle.short,
                        max_length=7,
                        required=False
                    )
                ]
            )
            
            await inter.response.send_modal(modal)
    
    @commands.Cog.listener("on_modal_submit")
    async def on_custom_role_modal_submit(self, inter: disnake.ModalInteraction):
        """Обработчик отправки формы для создания кастомной роли"""
        if inter.custom_id == "custom_role_modal":
            user_id = str(inter.author.id)
            
            # Получаем введенные данные
            role_name = inter.text_values["role_name"]
            role_color_hex = inter.text_values["role_color"]
            
            # Проверяем наличие достаточного количества очков
            if self.get_user_score(user_id) < 2500:
                await inter.response.send_message("У вас недостаточно очков для этой покупки!", ephemeral=True)
                return
            
            # Проверяем, что пользователь еще не покупал кастомную роль
            if self.has_made_purchase(user_id, "custom_role"):
                await inter.response.send_message("Вы уже приобрели кастомную роль!", ephemeral=True)
                return
            
            # Определяем цвет роли
            if role_color_hex and role_color_hex.startswith("#") and len(role_color_hex) == 7:
                try:
                    # Преобразуем HEX цвет в int для disnake
                    color = int(role_color_hex[1:], 16)
                except ValueError:
                    # Если указан неверный формат, используем случайный цвет
                    color = random.randint(0, 0xFFFFFF)
            else:
                # Если цвет не указан, используем случайный
                color = random.randint(0, 0xFFFFFF)
            
            try:
                # Создаем новую роль
                new_role = await inter.guild.create_role(
                    name=role_name,
                    color=disnake.Color(color),
                    reason=f"Кастомная роль для {inter.author.name} (ID: {user_id})"
                )
                
                # Добавляем роль пользователю
                await inter.author.add_roles(new_role)
                
                # Списываем очки
                self.score_data[user_id] -= 2500
                save_score_data(self.score_data)
                
                # Записываем покупку
                self.add_purchase(user_id, "custom_role")
                
                await inter.response.send_message(f"Поздравляем! Вы успешно создали кастомную роль **{role_name}**. С вашего счета списано 2500 очков.", ephemeral=True)
            except Exception as e:
                print(f"Ошибка при создании кастомной роли: {e}")
                await inter.response.send_message("Произошла ошибка при создании кастомной роли. Обратитесь к администратору.", ephemeral=True)

# Обработка ошибок
@bot.event
async def on_slash_command_error(inter: disnake.ApplicationCommandInteraction, error):
    if isinstance(error, commands.errors.CommandOnCooldown):
        await inter.response.send_message(
            f"Команда на перезарядке. Попробуйте снова через {error.retry_after:.1f} секунд.",
            ephemeral=True
        )
    elif isinstance(error, commands.errors.MissingPermissions):
        await inter.response.send_message(
            "У вас недостаточно прав для выполнения этой команды.",
            ephemeral=True
        )
    else:
        # Логирование других ошибок
        print(f"Ошибка при выполнении команды: {error}")
        await inter.response.send_message(
            "Произошла ошибка при выполнении команды. Попробуйте позже или обратитесь к администратору.",
            ephemeral=True
        )

# Регистрация когов
bot.add_cog(FriendCommands(bot))
bot.add_cog(ScoreCommands(bot))

# Запуск бота
if __name__ == "__main__":
    bot.run(TOKEN)
