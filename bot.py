import disnake
from disnake.ext import commands
import json
import os
from typing import List
from config import TOKEN, DATA_FILE

# Инициализация бота с синхронизацией команд
intents = disnake.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(
    command_prefix="/", 
    intents=intents, 
    test_guilds=[],  # Добавьте ID ваших серверов сюда для быстрой синхронизации команд
    sync_commands=True,
    sync_commands_debug=True
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

# Обработчики событий
@bot.event
async def on_ready():
    print(f"Бот готов к работе! Вход выполнен как {bot.user}")

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
        description="Показывает информацию о командах для управления друзьями"
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
        
        await inter.response.send_message(embed=embed, ephemeral=True)
    
    @commands.slash_command(
        name="addfriend",
        description="Добавить пользователя в список друзей"
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
        description="Удалить пользователя из списка друзей"
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
    
    @commands.slash_command(
        name="friendlist",
        description="Показать список друзей"
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
        description="Отправить уведомление о голосовом вызове всем друзьям"
    )
    async def callvoice(self, inter: disnake.ApplicationCommandInteraction):
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
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1234567890/1234567890/drink.png")  # Замените на реальный URL изображения напитка
        
        # Проверка, находится ли пользователь в голосовом канале
        voice_channel = None
        if inter.author.voice:
            voice_channel = inter.author.voice.channel
        
        # Отправка уведомлений всем друзьям
        sent_count = 0
        for friend_id in self.friend_data[user_id]:
            try:
                friend = await bot.fetch_user(int(friend_id))
                
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
        
        await inter.response.send_message(f"Уведомление о голосовом вызове отправлено {sent_count} друзьям.", ephemeral=True)

# Регистрация когов
bot.add_cog(FriendCommands(bot))

# Запуск бота
if __name__ == "__main__":
    bot.run(TOKEN)
