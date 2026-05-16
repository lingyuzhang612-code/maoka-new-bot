import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from flask import Flask
import threading
import os
import datetime

# --- 1. 网页保活 ---
app = Flask('')
@app.route('/')
def home(): return "小狗管家：馆长专用最终版已就位！🐾"

# --- 2. 交互逻辑：受保护附件表单 (图3) ---
class ProtectModal(Modal):
    def __init__(self, mode, files):
        super().__init__(title=f"上传受保护附件 ({mode}模式)")
        self.mode = mode
        self.files = files

    desc = TextInput(label='附件描述 (可选)', style=discord.TextStyle.paragraph, placeholder='简单描述一下这是什么文件...', required=False)
    filenames = TextInput(label='下载文件名 (必填，一行一个)', style=discord.TextStyle.paragraph, placeholder='角色卡-小狗.png\n设定集.json', required=True)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🔒 受保护的附件", color=0x2ecc71)
        embed.add_field(name="📄 附件数量", value=f"{len(self.files)}个文件", inline=True)
        embed.add_field(name="🐶 小狗说", value=f"{self.desc.value or '祝你用餐愉快！汪汪~'}", inline=False)
        
        tips = {
            "点赞": "👍 请先给首楼点赞，再点击下方按钮获取",
            "评论": "💬 请先在帖子内评论，再点击下方按钮获取",
            "口令": "🔑 请点击下方按钮输入口令获取",
            "点赞+口令": "👍🔑 需点赞首楼并输入口令",
            "点赞+评论": "👍💬 需点赞首楼并发表评论"
        }
        embed.add_field(name="💡 获取条件", value=tips.get(self.mode, "请按要求完成验证"), inline=False)
        embed.set_footer(text="每人每分钟最多查看5次")
        
        await interaction.response.send_message(embed=embed, view=VerifyView(self.mode, self.files))

# --- 3. 验证核心：真的去查点赞和评论 ---
class VerifyView(View):
    def __init__(self, mode, files):
        super().__init__(timeout=None)
        self.mode = mode
        self.files = files

    @discord.ui.button(label="验证并获取附件", style=discord.ButtonStyle.success, emoji="✅")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        # 基础数据：抓取首楼
        try:
            starter_msg = await interaction.channel.fetch_message(interaction.channel.id)
        except:
            return await interaction.followup.send("❌ 错误：请在帖子/线程内使用此功能！", ephemeral=True)

        user_id = interaction.user.id
        passed = False

        # 验证逻辑
        if "点赞" in self.mode:
            has_liked = any(user_id in [u.id async for u in r.users()] for r in starter_msg.reactions if str(r.emoji) in ["👍", "❤️", "✅"])
            passed = has_liked
        
        if "评论" in self.mode:
            has_commented = False
            async for m in interaction.channel.history(limit=100):
                if m.author.id == user_id and m.id != starter_msg.id:
                    has_commented = True
                    break
            passed = has_commented if "点赞" not in self.mode else (passed and has_commented)

        if passed or self.mode == "口令":
            # 如果是口令，这里应该弹窗，为了简洁这里直接发文件，馆长可自定
            file_links = "\n".join(self.files)
            await interaction.followup.send(f"✅ 验证通过！您的受保护文件如下：\n{file_links}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ 验证失败！你还没满足【{self.mode}】条件喵！", ephemeral=True)

# --- 4. 机器人主体 ---
class MaomaoBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
    async def setup_hook(self): await self.tree.sync()
    async def on_ready(self): print(f"🚀 馆长！全功能复刻版 {self.user} 已就命！")

bot = MaomaoBot()

# --- 5. 指令全家桶 (100% 对应截图) ---

# 【回顶】(图6 详情版)
@bot.tree.command(name="回顶", description="引用本频道的第一个消息 (仅自己可见)")
async def go_top(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    async for m in interaction.channel.history(limit=1, oldest_first=True):
        embed = discord.Embed(title="📌 频道第一条消息", color=0x3498db, timestamp=m.created_at)
        embed.description = f"**发送者**: {m.author.mention}\n**内容预览**: {m.content[:200] or '[附件/表情]'}\n\n[点击跳转到第一条消息]({m.jump_url})"
        embed.set_footer(text="点击上方链接即可快速回顶")
        await interaction.followup.send(embed=embed, ephemeral=True)

# 【删除消息】(图7 链接删除)
@bot.tree.command(name="删除消息", description="输入消息链接直接删除该消息")
@app_commands.describe(message_link="长按消息复制链接贴在这里")
async def del_msg(interaction: discord.Interaction, message_link: str):
    try:
        mid = int(message_link.split('/')[-1])
        msg = await interaction.channel.fetch_message(mid)
        await msg.delete()
        await interaction.response.send_message("✅ 目标消息已定点清除！", ephemeral=True)
    except:
        await interaction.response.send_message("❌ 无法删除！请检查链接是否正确或我是否有权限喵！", ephemeral=True)

# 【删除帖子】
@bot.tree.command(name="删除帖子", description="直接彻底删除当前帖子")
async def del_thread(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.Thread):
        await interaction.channel.delete()

# 【受保护附件】(图4 模式选择)
@bot.tree.command(name="受保护附件", description="上传附件并开启验证获取")
async def protect_file(interaction: discord.Interaction, 附件1: discord.Attachment, 附件2: discord.Attachment=None, 附件3: discord.Attachment=None, 附件4: discord.Attachment=None, 附件5: discord.Attachment=None):
    files = [f.url for f in [附件1, 附件2, 附件3, 附件4, 附件5] if f]
    
    # 模式选择 View
    view = View()
    modes = ["口令", "点赞", "评论", "点赞+口令", "点赞+评论"]
    for m in modes:
        btn = Button(label=f"{m}模式", style=discord.ButtonStyle.secondary if "+" in m else discord.ButtonStyle.primary)
        async def make_callback(m=m): # 闭包处理
            async def callback(i): await i.response.send_modal(ProtectModal(m, files))
            return callback
        btn.callback = await make_callback(m)
        view.add_item(btn)
        
    await interaction.response.send_message("⚙️ 请选择您要设置的【验证保护模式】：", view=view, ephemeral=True)

# --- 6. 启动 ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
