import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from flask import Flask
import threading
import os

# --- 1. 网页保活 ---
app = Flask('')
@app.route('/')
def home(): return "猫猫管家：这次再抓不住反应我就去流浪喵！🐾"

# --- 2. 交互逻辑：输入暗号弹窗 ---
class PasswordInputModal(Modal, title='🐱 猫猫管家：安全验证'):
    input_val = TextInput(label='请输入暗号', placeholder='暗号正确才会发资源给你喵...', required=True)
    def __init__(self, correct_pwd, files, needs_extra=None):
        super().__init__()
        self.correct_pwd = correct_pwd
        self.files = files
        self.needs_extra = needs_extra

    async def on_submit(self, interaction: discord.Interaction):
        # 如果需要额外检查“反应”
        if self.needs_extra == "reaction":
            try:
                # 在帖子(Thread)里，帖子ID就是首楼消息ID
                starter_msg = await interaction.channel.fetch_message(interaction.channel.id)
                has_any_reaction = False
                for reaction in starter_msg.reactions:
                    users = [u.id async for u in reaction.users()]
                    if interaction.user.id in users:
                        has_any_reaction = True
                        break
                if not has_any_reaction:
                    return await interaction.response.send_message("❌ 暗号对了，但你还没给首楼【添加反应】喵！", ephemeral=True)
            except:
                pass

        if self.input_val.value == self.correct_pwd:
            file_links = "\n".join(self.files)
            try:
                await interaction.user.send(f"🐱 **这是馆长托我发你的资源：**\n{file_links}")
                await interaction.response.send_message("✅ 验证成功！资源已私发，请检查私信喵！", ephemeral=True)
            except:
                await interaction.response.send_message(f"✅ 验证成功！私信失败，直接发这：\n{file_links}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 暗号不对喵！", ephemeral=True)

# --- 3. 核心：上传表单 ---
class ProtectModal(Modal):
    def __init__(self, mode, files):
        super().__init__(title=f"猫猫上传 - {mode}")
        self.mode = mode
        self.files = files

    desc = TextInput(label='附件描述 (可选)', style=discord.TextStyle.paragraph, placeholder='描述一下这是什么喵...', required=False)
    filenames = TextInput(label='下载文件名 (必填)', style=discord.TextStyle.paragraph, placeholder='角色卡.png\n设定集.json', required=True)
    pwd_setting = TextInput(label='设置暗号 (涉及口令模式必填)', placeholder='在这里设置你想要的验证口令...', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if "口令" in self.mode and not self.pwd_setting.value:
            return await interaction.response.send_message("❌ 馆长，选了口令模式必须设暗号喵！", ephemeral=True)

        embed = discord.Embed(title="🔒 受保护的附件", color=0x2ecc71)
        embed.add_field(name="📋 附件数量", value=f"{len(self.files)}个文件", inline=True)
        embed.add_field(name="🐱 猫猫说", value=f"{self.desc.value or '祝你用餐愉快喵！'}", inline=False)
        
        tips = {
            "口令模式": "🔑 请点击按钮输入正确暗号获取",
            "反应模式": "👍 请先给首楼添加【任意反应】，再点击下方验证",
            "评论模式": "💬 请先在帖子内评论，再点击下方验证",
            "反应+口令": "👍🔑 需添加反应并输入暗号",
            "反应+评论": "👍💬 需添加反应并在帖内评论"
        }
        embed.add_field(name="💡 获取条件", value=tips.get(self.mode, "请完成验证获取喵"), inline=False)
        embed.set_footer(text="每人每分钟最多查看5次 • 猫猫管家")
        await interaction.response.send_message(embed=embed, view=VerifyView(self.mode, self.files, self.pwd_setting.value))

# --- 4. 验证核心 ---
class VerifyView(View):
    def __init__(self, mode, files, correct_pwd):
        super().__init__(timeout=None)
        self.mode = mode
        self.files = files
        self.correct_pwd = correct_pwd

    @discord.ui.button(label="验证并获取附件", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 处理带暗号的情况
        if self.mode == "口令模式":
            return await interaction.response.send_modal(PasswordInputModal(self.correct_pwd, self.files))
        if self.mode == "反应+口令":
            return await interaction.response.send_modal(PasswordInputModal(self.correct_pwd, self.files, needs_extra="reaction"))

        await interaction.response.defer(ephemeral=True)
        
        try:
            # 稳妥抓取首楼消息
            starter_msg = await interaction.channel.fetch_message(interaction.channel.id)
            user_id = interaction.user.id
            
            # 1. 检查是否有任意“反应”
            has_reaction = False
            for r in starter_msg.reactions:
                users = [u.id async for u in r.users()]
                if user_id in users:
                    has_reaction = True
                    break
            
            # 2. 检查是否有评论
            has_comment = False
            async for m in interaction.channel.history(limit=50):
                if m.author.id == user_id and m.id != starter_msg.id:
                    has_comment = True
                    break

            # 3. 验证逻辑
            success = False
            if self.mode == "反应模式": success = has_reaction
            elif self.mode == "评论模式": success = has_comment
            elif self.mode == "反应+评论": success = (has_reaction and has_comment)

            if success:
                links = "\n".join(self.files)
                await interaction.user.send(f"🐱 **这是馆长托我发你的资源：**\n{links}")
                await interaction.followup.send("✅ 验证通过！资源已私发喵！", ephemeral=True)
            else:
                msg = "你还没给首楼添加【反应】喵！" if not has_reaction else "你还没发表评论喵！"
                await interaction.followup.send(f"❌ {msg}", ephemeral=True)
        except:
            await interaction.followup.send("❌ 出错啦！请确保你在帖子内点击，且我能读取首楼喵！", ephemeral=True)

# --- 5. 指令集 ---
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

@bot.tree.command(name="受保护附件")
async def protect_file(interaction: discord.Interaction, 附件1: discord.Attachment, 附件2: discord.Attachment=None, 附件3: discord.Attachment=None, 附件4: discord.Attachment=None, 附件5: discord.Attachment=None):
    files = [f.url for f in [附件1, 附件2, 附件3, 附件4, 附件5] if f]
    view = View()
    modes = ["口令模式", "反应模式", "评论模式", "反应+口令", "反应+评论"]
    for m in modes:
        btn = Button(label=m, style=discord.ButtonStyle.primary)
        async def make_cb(m=m):
            async def cb(i): await i.response.send_modal(ProtectModal(m, files))
            return cb
        btn.callback = await make_cb(m)
        view.add_item(btn)
    await interaction.response.send_message("⚙️ 猫猫管家：请选择保护模式：", view=view, ephemeral=True)

@bot.tree.command(name="删除帖子")
async def del_thread(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.Thread): await interaction.channel.delete()
    else: await interaction.response.send_message("这里不是帖子喵！", ephemeral=True)

@bot.tree.command(name="删除消息")
async def del_msg(interaction: discord.Interaction, 链接: str):
    try:
        mid = int(链接.split('/')[-1])
        msg = await interaction.channel.fetch_message(mid)
        await msg.delete()
        await interaction.response.send_message("✅ 定点爆破成功！", ephemeral=True)
    except: await interaction.response.send_message("❌ 链接不对喵！", ephemeral=True)

@bot.tree.command(name="回顶")
async def go_top(interaction: discord.Interaction):
    async for m in interaction.channel.history(limit=1, oldest_first=True):
        embed = discord.Embed(title="📌 频道第一条消息", color=0x3498db, description=f"[点击跳转]({m.jump_url})")
        await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
