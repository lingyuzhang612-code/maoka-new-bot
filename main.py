import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from flask import Flask
import threading
import os

# --- 1. 网页保活 ---
app = Flask('')
@app.route('/')
def home(): return "猫猫管家：馆长大人，猫猫回来戴罪立功了喵！🐾"

# --- 2. 交互逻辑：口令输入框 ---
class PasswordCheckModal(Modal, title='🔑 输入口令验证'):
    pwd_input = TextInput(label='口令', placeholder='请输入预设口令...', required=True)
    def __init__(self, files):
        super().__init__()
        self.files = files
    async def on_submit(self, interaction: discord.Interaction):
        if self.pwd_input.value == "123": # 这里可以自定义
            await interaction.response.send_message(f"✅ 口令正确！文件链接：\n" + "\n".join(self.files), ephemeral=True)
        else:
            await interaction.response.send_message("❌ 口令不对喵！", ephemeral=True)

# --- 3. 核心：受保护附件表单 (图3 猫猫版) ---
class ProtectModal(Modal):
    def __init__(self, mode, files):
        super().__init__(title=f"上传附件 - {mode}模式")
        self.mode = mode
        self.files = files

    desc = TextInput(label='附件描述 (可选)', style=discord.TextStyle.paragraph, placeholder='简单描述一下这是什么文件...', required=False)
    filenames = TextInput(label='下载文件名 (必填)', style=discord.TextStyle.paragraph, placeholder='角色卡.png\n设定集.json', required=True)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🔒 受保护的附件", color=0xff9900)
        embed.add_field(name="📄 附件数量", value=f"{len(self.files)}个文件", inline=True)
        embed.add_field(name="🐱 猫猫说", value=f"{self.desc.value or '祝你用餐愉快喵！'}", inline=False)
        
        tips = {
            "口令模式": "🔑 请点击按钮输入口令获取",
            "点赞模式": "👍 请先给首楼点赞，再点击下方按钮获取",
            "评论模式": "💬 请先在帖子内评论，再点击下方按钮获取",
            "点赞+口令模式": "👍🔑 需点赞首楼并输入口令",
            "点赞+评论模式": "👍💬 需点赞首楼并发表评论"
        }
        embed.add_field(name="💡 获取条件", value=tips.get(self.mode, "请按要求完成验证喵"), inline=False)
        embed.set_footer(text="每人每分钟最多查看5次")
        await interaction.response.send_message(embed=embed, view=VerifyView(self.mode, self.files))

# --- 4. 验证核心逻辑 (修复了不回复的问题) ---
class VerifyView(View):
    def __init__(self, mode, files):
        super().__init__(timeout=None)
        self.mode = mode
        self.files = files

    @discord.ui.button(label="验证并获取附件", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 如果是口令模式，直接弹窗
        if "口令" in self.mode and "+" not in self.mode:
            return await interaction.response.send_modal(PasswordCheckModal(self.files))

        await interaction.response.defer(ephemeral=True)
        
        # 抓取数据
        try:
            starter_msg = await interaction.channel.fetch_message(interaction.channel.id)
        except:
            return await interaction.followup.send("❌ 请在帖子内使用此验证喵！", ephemeral=True)

        user_id = interaction.user.id
        has_liked = any(user_id in [u.id async for u in r.users()] for r in starter_msg.reactions if str(r.emoji) in ["👍", "❤️", "✅"])
        
        has_commented = False
        if "评论" in self.mode:
            async for m in interaction.channel.history(limit=50):
                if m.author.id == user_id and m.id != starter_msg.id:
                    has_commented = True
                    break

        # 判断是否通过
        success = False
        if self.mode == "点赞模式": success = has_liked
        elif self.mode == "评论模式": success = has_commented
        elif self.mode == "点赞+评论模式": success = (has_liked and has_commented)

        if success:
            await interaction.followup.send(f"✅ 验证通过！您的文件链接：\n" + "\n".join(self.files), ephemeral=True)
        else:
            await interaction.followup.send(f"❌ 还没完成【{self.mode}】哦，快去点赞/评论喵！", ephemeral=True)

# --- 5. 机器人主体 ---
class MaomaoBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
    async def setup_hook(self): await self.tree.sync()

bot = MaomaoBot()

# --- 6. 指令全家桶 (复刻版) ---

@bot.tree.command(name="回顶", description="引用频道第一条消息 (猫猫版)")
async def go_top(interaction: discord.Interaction):
    async for m in interaction.channel.history(limit=1, oldest_first=True):
        embed = discord.Embed(title="📌 频道第一条消息", color=0x3498db, timestamp=m.created_at)
        embed.description = f"**发送者**: {m.author.mention}\n**内容**: {m.content[:150]}\n\n[点击跳转到第一条消息]({m.jump_url})"
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="删除消息", description="通过链接直接删除消息")
async def del_msg(interaction: discord.Interaction, message_link: str):
    try:
        mid = int(message_link.split('/')[-1])
        msg = await interaction.channel.fetch_message(mid)
        await msg.delete()
        await interaction.response.send_message("✅ 消息已定点爆破！", ephemeral=True)
    except:
        await interaction.response.send_message("❌ 链接不对或没权限喵！", ephemeral=True)

@bot.tree.command(name="受保护附件", description="上传附件并开启验证")
async def protect_file(interaction: discord.Interaction, 附件1: discord.Attachment, 附件2: discord.Attachment=None, 附件3: discord.Attachment=None, 附件4: discord.Attachment=None, 附件5: discord.Attachment=None):
    files = [f.url for f in [附件1, 附件2, 附件3, 附件4, 附件5] if f]
    view = View()
    modes = ["口令模式", "点赞模式", "评论模式", "点赞+口令模式", "点赞+评论模式"]
    for m in modes:
        btn = Button(label=m, style=discord.ButtonStyle.primary)
        async def make_callback(m=m):
            async def callback(i): await i.response.send_modal(ProtectModal(m, files))
            return callback
        btn.callback = await make_callback(m)
        view.add_item(btn)
    await interaction.response.send_message("⚙️ 猫猫管家提醒：请选择验证模式：", view=view, ephemeral=True)

# --- 7. 启动 ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
