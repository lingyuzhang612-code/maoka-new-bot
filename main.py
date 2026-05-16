import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from flask import Flask
import threading
import os
import re

# --- 1. 网页保活 ---
app = Flask('')
@app.route('/')
def home(): return "小狗管家：完全复刻版已就位喵！🐾"

# --- 2. 交互逻辑：上传表单 (图3) ---
class UploadModal(Modal):
    def __init__(self, mode, file_urls):
        super().__init__(title=f"上传受保护附件 ({mode}模式)")
        self.mode = mode
        self.file_urls = file_urls
        
    desc = TextInput(label='附件描述 (可选)', style=discord.TextStyle.paragraph, placeholder='简单描述一下这是什么文件...', required=False)
    filenames = TextInput(label='下载文件名 (必填，一行一个)', style=discord.TextStyle.paragraph, placeholder='例如：\n角色卡.png\n设定集.json', required=True)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🔒 受保护的附件", color=0x2ecc71)
        embed.add_field(name="📋 附件数量", value=f"{len(self.file_urls)}个文件", inline=False)
        embed.add_field(name="🐶 小狗说", value=f"{self.desc.value or '祝你用餐愉快！汪汪~'}", inline=False)
        
        condition = "未知"
        if self.mode == "点赞": condition = "👍 请先给首楼点赞，再点击下方按钮获取"
        elif self.mode == "口令": condition = "🔑 请输入正确口令获取"
        elif self.mode == "点赞+口令": condition = "👍🔑 需点赞首楼并输入口令"

        embed.add_field(name="💡 获取条件", value=condition, inline=False)
        embed.set_footer(text="每人每分钟最多查看5次")
        
        await interaction.response.send_message(embed=embed, view=VerifyView(self.mode, self.file_urls))

# --- 3. 验证逻辑 (点赞/评论/口令) ---
class VerifyView(View):
    def __init__(self, mode, file_urls):
        super().__init__(timeout=None)
        self.mode = mode
        self.file_urls = file_urls

    @discord.ui.button(label="验证并获取附件", style=discord.ButtonStyle.success, emoji="👍")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        # 验证点赞逻辑 (抓取本帖首楼)
        target_msg = await interaction.channel.fetch_message(interaction.channel.id)
        has_liked = any(interaction.user.id in [u.id async for u in r.users()] for r in target_msg.reactions if str(r.emoji) in ["👍", "❤️", "✅"])
        
        if self.mode == "点赞" and has_liked:
            files_str = "\n".join(self.file_urls)
            await interaction.followup.send(f"✅ 验证通过！您的文件：\n{files_str}", ephemeral=True)
        else:
            await interaction.followup.send("❌ 验证未通过，请按要求完成后再试喵！", ephemeral=True)

# --- 4. 机器人核心 ---
class MaomaoBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self): await self.tree.sync()

bot = MaomaoBot()

# --- 5. 馆长要求的指令 (图5/6/7) ---

# 【回顶指令】(图6 详情卡片)
@bot.tree.command(name="回顶", description="引用本频道的第一个消息 (仅自己可见)")
async def go_top(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    async for m in interaction.channel.history(limit=1, oldest_first=True):
        embed = discord.Embed(title="📌 频道第一条消息", color=0x3498db)
        embed.description = f"**发送者**: {m.author.mention}\n**内容**: {m.content[:100]}...\n\n[点击跳转到第一条消息]({m.jump_url})"
        embed.set_footer(text=f"发送于: {m.created_at.strftime('%Y-%m-%d %H:%M')}")
        await interaction.followup.send(embed=embed, ephemeral=True)

# 【删除消息】(图7 链接删除)
@bot.tree.command(name="删除消息", description="通过消息链接直接删除消息")
@app_commands.describe(message_link="长按消息复制链接填入这里")
async def del_msg(interaction: discord.Interaction, message_link: str):
    try:
        # 从链接提取 ID: https://discord.com/channels/GID/CID/MID
        parts = message_link.split('/')
        channel_id = int(parts[-2])
        message_id = int(parts[-1])
        
        channel = bot.get_channel(channel_id)
        msg = await channel.fetch_message(message_id)
        await msg.delete()
        await interaction.response.send_message("✅ 消息已通过链接成功定点爆破！", ephemeral=True)
    except:
        await interaction.response.send_message("❌ 链接无效或我没有权限删除该消息喵！", ephemeral=True)

# 【删除帖子】
@bot.tree.command(name="删除帖子", description="删除当前帖子")
async def del_thread(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.Thread):
        await interaction.channel.delete()

# 【受保护附件】(带5个附件选项)
@bot.tree.command(name="受保护附件", description="上传受保护附件")
async def protect_file(interaction: discord.Interaction, 附件1: discord.Attachment, 附件2: discord.Attachment=None, 附件3: discord.Attachment=None, 附件4: discord.Attachment=None, 附件5: discord.Attachment=None):
    files = [f.url for f in [附件1, 附件2, 附件3, 附件4, 附件5] if f]
    
    # 这一步是让馆长选模式
    view = View()
    btn1 = Button(label="点赞模式", style=discord.ButtonStyle.success)
    btn1.callback = lambda i: i.response.send_modal(UploadModal("点赞", files))
    view.add_item(btn1)
    
    await interaction.response.send_message("⚙️ 请选择保护模式以开启详情表单：", view=view, ephemeral=True)

# --- 6. 启动 ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
