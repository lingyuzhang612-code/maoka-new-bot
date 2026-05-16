import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from flask import Flask
import threading
import os

# --- 1. 网页保活 ---
app = Flask('')
@app.route('/')
def home(): return "超级猫猫管家：全功能终极合体版已就位喵！🐾"

# ======================================================
# --- 2. 核心：受保护附件 (您最关心的发资源逻辑) ---
# ======================================================
class PasswordInputModal(Modal, title='🐱 猫猫管家：安全验证'):
    input_val = TextInput(label='请输入暗号', placeholder='暗号正确才会发资源给你喵...', required=True)
    def __init__(self, correct_pwd, files, needs_extra=None):
        super().__init__()
        self.correct_pwd = correct_pwd
        self.files = files
        self.needs_extra = needs_extra

    async def on_submit(self, interaction: discord.Interaction):
        if self.needs_extra == "reaction":
            try:
                starter_msg = await interaction.channel.fetch_message(interaction.channel.id)
                has_any_reaction = any(interaction.user.id in [u.id async for u in r.users()] for r in starter_msg.reactions)
                if not has_any_reaction:
                    return await interaction.response.send_message("❌ 暗号对了，但你还没给首楼【添加反应】喵！", ephemeral=True)
            except: pass

        if self.input_val.value == self.correct_pwd:
            file_links = "\n".join(self.files)
            try:
                await interaction.user.send(f"🐱 **这是馆长托我发你的资源：**\n{file_links}")
                await interaction.response.send_message("✅ 验证成功！资源已私发喵！", ephemeral=True)
            except:
                await interaction.response.send_message(f"✅ 验证成功！直接发这：\n{file_links}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 暗号不对喵！", ephemeral=True)

class ProtectModal(Modal):
    def __init__(self, mode, files):
        super().__init__(title=f"猫猫上传 - {mode}")
        self.mode = mode
        self.files = files
    desc = TextInput(label='附件描述 (可选)', style=discord.TextStyle.paragraph, placeholder='描述一下这是什么喵...', required=False)
    filenames = TextInput(label='下载文件名 (必填)', placeholder='角色卡.png', required=True)
    pwd_setting = TextInput(label='设置暗号', placeholder='涉及口令模式必填...', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if "口令" in self.mode and not self.pwd_setting.value:
            return await interaction.response.send_message("❌ 选了口令模式必须设暗号喵！", ephemeral=True)
        embed = discord.Embed(title="🔒 受保护的附件", color=0x2ecc71)
        embed.add_field(name="📋 附件数量", value=f"{len(self.files)}个文件", inline=True)
        embed.add_field(name="🐱 猫猫说", value=f"{self.desc.value or '祝你用餐愉快喵！'}", inline=False)
        tips = {"口令模式": "🔑 请点按钮输口令", "反应模式": "👍 请给首楼【添加反应】", "评论模式": "💬 请在帖内评论", "反应+口令": "👍🔑 反应并输口令", "反应+评论": "👍💬 反应并评论"}
        embed.add_field(name="💡 获取条件", value=tips.get(self.mode, "请验证"), inline=False)
        await interaction.response.send_message(embed=embed, view=VerifyView(self.mode, self.files, self.pwd_setting.value))

class VerifyView(View):
    def __init__(self, mode, files, correct_pwd):
        super().__init__(timeout=None)
        self.mode = mode
        self.files = files
        self.correct_pwd = correct_pwd

    @discord.ui.button(label="验证并获取附件", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_btn(self, interaction: discord.Interaction, button: Button):
        if self.mode == "口令模式": return await interaction.response.send_modal(PasswordInputModal(self.correct_pwd, self.files))
        if self.mode == "反应+口令": return await interaction.response.send_modal(PasswordInputModal(self.correct_pwd, self.files, needs_extra="reaction"))
        await interaction.response.defer(ephemeral=True)
        try:
            starter_msg = await interaction.channel.fetch_message(interaction.channel.id)
            user_id = interaction.user.id
            has_reaction = any(user_id in [u.id async for u in r.users()] for r in starter_msg.reactions)
            has_comment = False
            if "评论" in self.mode:
                async for m in interaction.channel.history(limit=50):
                    if m.author.id == user_id and m.id != starter_msg.id:
                        has_comment = True; break
            success = (self.mode=="反应模式" and has_reaction) or (self.mode=="评论模式" and has_comment) or (self.mode=="反应+评论" and has_reaction and has_comment)
            if success:
                links = "\n".join(self.files)
                try: await interaction.user.send(f"🐱 资源已私发：\n{links}")
                except: await interaction.followup.send(f"✅ 验证成功：\n{links}", ephemeral=True)
            else: await interaction.followup.send("❌ 条件未达成喵！", ephemeral=True)
        except: await interaction.followup.send("❌ 请在帖子内使用喵！", ephemeral=True)

# ======================================================
# --- 3. 核心：成人验证 (支付宝截图 + 答题人工审核) ---
# ======================================================
class AdultReviewView(View):
    def __init__(self, target_member):
        super().__init__(timeout=None)
        self.target_member = target_member

    @discord.ui.button(label="通过审核", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: Button):
        role = discord.utils.get(interaction.guild.roles, name="吃吃小猫")
        if role:
            await self.target_member.add_roles(role)
            await interaction.response.send_message(f"🎊 审核通过！已为 {self.target_member.mention} 发放【吃吃小猫】身份组！")
            self.stop()
        else: await interaction.response.send_message("❌ 没找到‘吃吃小猫’身份组喵！")

class AdultApplyView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="开启成人验证", style=discord.ButtonStyle.primary, emoji="🔞", custom_id="adult_v")
    async def apply(self, interaction: discord.Interaction, button: Button):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await interaction.guild.create_text_channel(name=f"成人验证-{interaction.user.name}", overwrites=overwrites, category=interaction.channel.category)
        embed = discord.Embed(title="🔞 成人认证·支付宝审核", color=0xe91e63)
        embed.description = (
            "请在本频道完成以下操作：\n\n"
            "1. **发送截图**：支付宝-我的-个人信息（需显示年龄20+）\n"
            "2. **回答问题**（直接回复）：\n"
            "- 看到有人倒卖/二传角色卡你会怎么做？\n"
            "- 如果作者标注“禁止二改”，你该如何遵守？\n\n"
            "完成后请艾特管理进行审核！"
        )
        await channel.send(embed=embed, view=AdultReviewView(interaction.user))
        await interaction.response.send_message(f"✅ 验证通道已开启：{channel.mention}", ephemeral=True)

# ======================================================
# --- 4. 核心：身份认证中心 (小猫系列) ---
# ======================================================
class IdentityApplyModal(Modal):
    def __init__(self, role_name):
        super().__init__(title=f"申请【{role_name}】认证")
        self.role_name = role_name
    link = TextInput(label='作品链接', placeholder='粘贴获得5个反应的作品帖子链接...', required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            parts = self.link.value.split('/')
            target_msg = await interaction.client.get_channel(int(parts[-2])).fetch_message(int(parts[-1]))
            if target_msg.author.id != interaction.user.id: return await interaction.followup.send("❌ 非本人作品！")
            if sum(r.count for r in target_msg.reactions) >= 5:
                role = discord.utils.get(interaction.guild.roles, name=self.role_name)
                await interaction.user.add_roles(role)
                await interaction.followup.send(f"🎉 已发放【{self.role_name}】头衔！")
            else: await interaction.followup.send("💡 反应不够 5 个。")
        except: await interaction.followup.send("❌ 链接无效。")

class IdentityCenterView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="创作者小猫", style=discord.ButtonStyle.primary, custom_id="c1")
    async def c1(self, i, b): await i.response.send_modal(IdentityApplyModal("创作者小猫"))
    @discord.ui.button(label="维修小猫", style=discord.ButtonStyle.success, custom_id="c2")
    async def c2(self, i, b): await i.response.send_modal(IdentityApplyModal("维修小猫"))
    @discord.ui.button(label="铲屎官", style=discord.ButtonStyle.secondary, custom_id="c3")
    async def c3(self, i, b): await i.response.send_modal(IdentityApplyModal("铲屎官"))
    @discord.ui.button(label="做图小猫", style=discord.ButtonStyle.danger, custom_id="c4")
    async def c4(self, i, b): await i.response.send_modal(IdentityApplyModal("做图小猫"))

# ======================================================
# --- 5. 机器人主体与所有指令合体 ---
# ======================================================
class MaomaoBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.reactions = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(AdultApplyView())
        self.add_view(IdentityCenterView())
        await self.tree.sync()

bot = MaomaoBot()

@bot.tree.command(name="受保护附件")
async def protect_file(interaction: discord.Interaction, 附件1: discord.Attachment, 附件2: discord.Attachment=None, 附件3: discord.Attachment=None, 附件4: discord.Attachment=None, 附件5: discord.Attachment=None):
    files = [f.url for f in [附件1, 附件2, 附件3, 附件4, 附件5] if f]
    view = View()
    modes = ["口令模式", "反应模式", "评论模式", "反应+口令", "反应+评论"]
    for m in modes:
        btn = Button(label=m, style=discord.ButtonStyle.primary)
        async def mk_cb(m=m):
            async def cb(i): await i.response.send_modal(ProtectModal(m, files))
            return cb
        btn.callback = await mk_cb()
        view.add_item(btn)
    await interaction.response.send_message("⚙️ 猫猫管家：请选择保护模式：", view=view, ephemeral=True)

@bot.tree.command(name="发送认证中心")
async def send_id_center(interaction: discord.Interaction):
    embed = discord.Embed(title="✨ 创作者身份认证中心", color=0x9b59b6, description="发帖获5个反应即可在此申请头衔喵！")
    await interaction.response.send_message(embed=embed, view=IdentityCenterView())

@bot.tree.command(name="初始化成人验证")
async def init_adult(interaction: discord.Interaction):
    embed = discord.Embed(title="🔞 成人认证中心", color=0x000000, description="本区需20+认证。点击下方按钮开启私人频道，发送支付宝年龄截图及答题。")
    await interaction.response.send_message(embed=embed, view=AdultApplyView())

@bot.tree.command(name="封禁公示")
async def ban(interaction: discord.Interaction, 用户: discord.Member, 理由: str):
    embed = discord.Embed(title="⚖️ 封禁公示", color=0x992d22)
    embed.add_field(name="违规用户", value=用户.mention, inline=False)
    embed.add_field(name="理由", value=理由, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="删除帖子")
async def del_thread(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.Thread): await interaction.channel.delete()

@bot.tree.command(name="删除消息")
async def del_msg(interaction: discord.Interaction, 链接: str):
    try:
        mid = int(链接.split('/')[-1])
        msg = await interaction.channel.fetch_message(mid)
        await msg.delete()
        await interaction.response.send_message("✅ 已爆破！", ephemeral=True)
    except: await interaction.response.send_message("❌ 失败喵！", ephemeral=True)

@bot.tree.command(name="回顶")
async def go_top(interaction: discord.Interaction):
    async for m in interaction.channel.history(limit=1, oldest_first=True):
        await interaction.response.send_message(f"📌 [跳转首楼]({m.jump_url})", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
