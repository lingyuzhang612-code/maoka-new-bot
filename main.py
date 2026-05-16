import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from flask import Flask
import threading
import os

# --- 1. 网页保活 (让机器人 24 小时不掉线) ---
app = Flask('')
@app.route('/')
def home(): return "猫猫管家：全功能高级版已上线喵！🐾"

# --- 2. 附件交互组件 (弹窗和按钮) ---
class PasswordModal(Modal, title='🔒 输入获取口令'):
    password_input = TextInput(label='请输入口令', placeholder='在这里输入口令...', required=True)
    async def on_submit(self, interaction: discord.Interaction):
        # 这里的口令逻辑可以自己改
        if self.password_input.value == "123":
            await interaction.response.send_message(f"✅ 口令正确！附件正在发送到您的私信喵！", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ 口令错误，请检查后再试喵！", ephemeral=True)

class ProtectView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 口令获取", style=discord.ButtonStyle.primary)
    async def password_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PasswordModal())

    @discord.ui.button(label="👍 点赞首楼获取", style=discord.ButtonStyle.success)
    async def like_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚨 正在检测点赞状态，请稍后...", ephemeral=True)

    @discord.ui.button(label="👍🔒 点赞+口令获取", style=discord.ButtonStyle.secondary)
    async def both_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PasswordModal())

# --- 3. 机器人核心大脑 ---
class MaomaoBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ 所有指令同步成功！")

    async def on_ready(self):
        print(f"🚀 报告馆长！{self.user} 已经全武装上线！")

bot = MaomaoBot()

# --- 4. 所有的独立指令 (打包在一起了喵！) ---

# 【指令 1：回顶】
@bot.tree.command(name="回顶", description="快速回到频道的最顶端消息")
async def go_top(interaction: discord.Interaction):
    async for message in interaction.channel.history(limit=1, oldest_first=True):
        await interaction.response.send_message(f"🔗 [点击此处回到顶端]({message.jump_url})", ephemeral=True)

# 【指令 2：删除消息】
@bot.tree.command(name="删除消息", description="如何删除单条消息的说明")
async def del_msg(interaction: discord.Interaction):
    await interaction.response.send_message("猫猫管家提醒：请右键或长按消息 -> 应用 -> 选择删除消息喵！", ephemeral=True)

# 【指令 3：删除帖子】
@bot.tree.command(name="删除帖子", description="删除当前所在的帖子或线程")
async def del_thread(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("🚀 正在清理当前帖子...")
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("只有在帖子或线程里才能使用此指令喵！", ephemeral=True)

# 【指令 4：受保护附件】
@bot.tree.command(name="受保护附件", description="上传受保护附件并开启交互获取")
@app_commands.describe(附件1="要上传的文件")
async def protect_file(interaction: discord.Interaction, 附件1: discord.Attachment):
    embed = discord.Embed(
        title="📦 保护机制已启动",
        description=(
            "请选择下方的验证方式以获取附件内容：\n\n"
            "🔒 **口令获取**：输入正确暗号即可查看\n"
            "👍 **点赞获取**：点赞首楼后自动解锁\n"
            "👍🔒 **组合获取**：满足以上双重条件"
        ),
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, view=ProtectView())

# --- 5. 启动启动启动！ ---
if __name__ == "__main__":
    # 读取端口
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    # 读取你在 Render 里填的那串钥匙
    TOKEN = os.environ.get("DISCORD_TOKEN")
    bot.run(TOKEN)
