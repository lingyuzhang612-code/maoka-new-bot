import discord
from discord import app_commands
from flask import Flask
import threading
import os

# --- 1. 网页保活 ---
app = Flask('')
@app.route('/')
def home(): return "猫猫管家：搬家已安顿好喵！🐾"

# --- 2. 机器人核心 ---
class MaomaoBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ 猫猫管家独立指令同步完成！")

    async def on_ready(self):
        print(f"🚀 搬家成功！我是：{self.user}")

bot = MaomaoBot()

# --- 3. 指令部分 (保持不变) ---
@bot.tree.command(name="回顶", description="回到频道最顶端消息")
async def go_top(interaction: discord.Interaction):
    async for message in interaction.channel.history(limit=1, oldest_first=True):
        await interaction.response.send_message(f"🔗 [回到最顶端]({message.jump_url})", ephemeral=True)

@bot.tree.command(name="删除消息", description="删除指定的单条消息")
async def del_msg(interaction: discord.Interaction):
    await interaction.response.send_message("猫猫管家：请右键消息 -> 应用 -> 选择删除喵！", ephemeral=True)

@bot.tree.command(name="删除帖子", description="删除当前帖子/线程")
async def del_thread(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("🚀 正在清理该帖子...")
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("此地不可删除喵！", ephemeral=True)

@bot.tree.command(name="受保护附件", description="上传受保护的1-5个附件")
@app_commands.describe(附件1="必填", 附件2="可选", 附件3="可选", 附件4="可选", 附件5="可选")
async def protect_file(interaction: discord.Interaction, 附件1: discord.Attachment, 附件2: discord.Attachment=None, 附件3: discord.Attachment=None, 附件4: discord.Attachment=None, 附件5: discord.Attachment=None):
    embed = discord.Embed(title="📦 受保护附件已就位", description="请验证后查看喵！", color=0xff9900)
    await interaction.response.send_message(embed=embed)

# --- 4. 启动启动！ ---
if __name__ == "__main__":
    # 读取 Render 分配的端口
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    # 【核心修改】这里不再填钥匙，而是去读 Render 的格子！
    TOKEN = os.environ.get("DISCORD_TOKEN")
    bot.run(TOKEN)
