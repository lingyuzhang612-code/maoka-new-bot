import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from flask import Flask
import threading
import os

# --- 1. 网页保活 ---
app = Flask('')
@app.route('/')
def home(): return "猫猫管家：全功能验证+私信版已就位！🐾"

# --- 2. 交互逻辑：输入口令的弹窗 ---
class PasswordInputModal(Modal, title='🐱 猫猫管家：暗号验证'):
    input_val = TextInput(label='请输入暗号', placeholder='输入馆长设置的口令...', required=True)
    def __init__(self, correct_pwd, files, needs_extra=None):
        super().__init__()
        self.correct_pwd = correct_pwd
        self.files = files
        self.needs_extra = needs_extra # 用于点赞+口令的额外检查

    async def on_submit(self, interaction: discord.Interaction):
        # 如果有额外条件（比如点赞），先检查
        if self.needs_extra == "like":
            starter_msg = await interaction.channel.fetch_message(interaction.channel.id)
            liked = any(interaction.user.id in [u.id async for u in r.users()] for r in starter_msg.reactions if str(r.emoji) in ["👍", "❤️", "✅"])
            if not liked:
                return await interaction.response.send_message("❌ 暗号对了，但你还没给首楼【点赞】喵！", ephemeral=True)

        if self.input_val.value == self.correct_pwd:
            try:
                # 【验证成功：发私信】
                links = "\n".join(self.files)
                await interaction.user.send(f"🐱 **这是馆长托我发你的资源：**\n{links}")
                await interaction.response.send_message("✅ 验证成功！资源已私发，请查收喵！", ephemeral=True)
            except:
                await interaction.response.send_message(f"✅ 验证成功！但发不了私信，直接给你：\n" + "\n".join(self.files), ephemeral=True)
        else:
            await interaction.response.send_message("❌ 暗号不对喵！", ephemeral=True)

# --- 3. 核心：上传表单 (图3 完美复刻) ---
class ProtectModal(Modal):
    def __init__(self, mode, files):
        super().__init__(title=f"猫猫上传 - {mode}")
        self.mode = mode
        self.files = files

    desc = TextInput(label='附件描述 (可选)', style=discord.TextStyle.paragraph, placeholder='描述一下这是什么喵...', required=False)
    filenames = TextInput(label='下载文件名 (必填)', style=discord.TextStyle.paragraph, placeholder='例如：\n角色卡.png\n设定集.json', required=True)
    pwd_setting = TextInput(label='设置验证口令 (若涉及口令模式则必填)', placeholder='在这里输入你预设的暗号...', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if "口令" in self.mode and not self.pwd_setting.value:
            return await interaction.response.send_message("❌ 选了口令模式必须设置口令喵！", ephemeral=True)

        embed = discord.Embed(title="🔒 受保护的附件", color=0x2ecc71)
        embed.add_field(name="📋 附件数量", value=f"{len(self.files)}个文件", inline=True)
        embed.add_field(name="🐱 猫猫说", value=f"{self.desc.value or '祝你用餐愉快喵！'}", inline=False)
        
        tips = {
            "口令模式": "🔑 请点击按钮输入正确暗号获取",
            "点赞模式": "👍 请先给首楼点赞，再点击下方验证",
            "评论模式": "💬 请先在帖子内评论，再点击下方验证",
            "点赞+口令模式": "👍🔑 需点赞首楼并输入暗号",
            "点赞+评论模式": "👍💬 需点赞首楼并在帖内评论"
        }
        embed.add_field(name="💡 获取条件", value=tips.get(self.mode, "请按要求完成验证喵"), inline=False)
        embed.set_footer(text="每人每分钟最多查看5次 • 猫猫管家")
        await interaction.response.send_message(embed=embed, view=VerifyView(self.mode, self.files, self.pwd_setting.value))

# --- 4. 验证逻辑：点赞、评论、混合检查 ---
class VerifyView(View):
    def __init__(self, mode, files, correct_pwd):
        super().__init__(timeout=None)
        self.mode = mode
        self.files = files
        self.correct_pwd = correct_pwd

    @discord.ui.button(label="验证并获取附件", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 情况 A：纯口令模式
        if self.mode == "口令模式":
            return await interaction.response.send_modal(PasswordInputModal(self.correct_pwd, self.files))
        
        # 情况 B：点赞+口令
        if self.mode == "点赞+口令模式":
            return await interaction.response.send_modal(PasswordInputModal(self.correct_pwd, self.files, needs_extra="like"))

        await interaction.response.defer(ephemeral=True)
        
        try:
            # 抓取数据
            starter_msg = await interaction.channel.fetch_message(interaction.channel.id)
            user_id = interaction.user.id
            
            # 1. 检查点赞 (👍 ❤️ ✅)
            liked = any(user_id in [u.id async for u in r.users()] for r in starter_msg.reactions if str(r.emoji) in ["👍", "❤️", "✅"])
            
            # 2. 检查评论 (除了首楼以外的消息)
            commented = False
            async for m in interaction.channel.history(limit=50):
                if m.author.id == user_id and m.id != starter_msg.id:
                    commented = True
                    break

            # 3. 验证逻辑汇总
            can_pass = False
            if self.mode == "点赞模式": can_pass = liked
            elif self.mode == "评论模式": can_pass = commented
            elif self.mode == "点赞+评论模式": can_pass = (liked and commented)

            if can_pass:
                links = "\n".join(self.files)
                await interaction.user.send(f"🐱 **这是馆长托我发你的资源：**\n{links}")
                await interaction.followup.send("✅ 验证通过！资源已私发喵！", ephemeral=True)
            else:
                msg = "你还没点赞喵！" if "点赞" in self.mode and not liked else "你还没评论喵！"
                if "点赞+评论" in self.mode and (not liked or not commented):
                    msg = "点赞和评论都要完成喵！"
                await interaction.followup.send(f"❌ {msg}", ephemeral=True)
        except:
            await interaction.followup.send("❌ 出错啦，请确保在帖子内点击喵！", ephemeral=True)

# --- 5. 机器人主体与指令 ---
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

@bot.tree.command(name="受保护附件", description="上传附件并开启各种验证模式")
async def protect_file(interaction: discord.Interaction, 附件1: discord.Attachment, 附件2: discord.Attachment=None, 附件3: discord.Attachment=None, 附件4: discord.Attachment=None, 附件5: discord.Attachment=None):
    files = [f.url for f in [附件1, 附件2, 附件3, 附件4, 附件5] if f]
    view = View()
    modes = ["口令模式", "点赞模式", "评论模式", "点赞+口令模式", "点赞+评论模式"]
    for m in modes:
        btn = Button(label=m, style=discord.ButtonStyle.primary)
        async def make_cb(m=m):
            async def cb(i): await i.response.send_modal(ProtectModal(m, files))
            return cb
        btn.callback = await make_cb(m)
        view.add_item(btn)
    await interaction.response.send_message("⚙️ 猫猫管家：请选择保护模式：", view=view, ephemeral=True)

@bot.tree.command(name="回顶")
async def go_top(interaction: discord.Interaction):
    async for m in interaction.channel.history(limit=1, oldest_first=True):
        embed = discord.Embed(title="📌 频道第一条消息", color=0x3498db, description=f"**内容**: {m.content[:100]}\n\n[点击跳转]({m.jump_url})")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="删除消息")
async def del_msg(interaction: discord.Interaction, 链接: str):
    try:
        mid = int(链接.split('/')[-1])
        msg = await interaction.channel.fetch_message(mid)
        await msg.delete()
        await interaction.response.send_message("✅ 已定点爆破喵！", ephemeral=True)
    except: await interaction.response.send_message("❌ 链接无效喵！", ephemeral=True)

@bot.tree.command(name="删除帖子")
async def del_thread(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.Thread): await interaction.channel.delete()

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
