import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from flask import Flask
import threading
import os

# --- 1. 网页保活 ---
app = Flask('')
@app.route('/')
def home(): return "超级猫猫管家：硬核入馆政审版已就位喵！🐾"

# ======================================================
# --- 2. 核心：硬核成人验证 (支付宝截图 + 专业考核题) ---
# ======================================================
class AdultReviewView(View):
    """管理员专用审核按钮"""
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="【审核通过】发放吃吃小猫", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, i, b):
        if not i.user.guild_permissions.administrator: return await i.response.send_message("❌ 只有管理员能点这个喵！", ephemeral=True)
        role = discord.utils.get(i.guild.roles, name="吃吃小猫")
        if role:
            await self.member.add_roles(role)
            await i.response.send_message(f"🎊 **政审通过！**\n已为 {self.member.mention} 发放【吃吃小猫】身份！欢迎新大佬！")
            b.disabled = True
            await i.message.edit(view=self)
        else: await i.response.send_message("❌ 报错：没找到‘吃吃小猫’身份组喵！")

class AdultApplyView(View):
    """验证入口面板"""
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="开启成人认证 & 专业考核", style=discord.ButtonStyle.primary, emoji="🔞", custom_id="adult_pro_v")
    async def apply(self, i, b):
        overwrites = {
            i.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            i.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ch = await i.guild.create_text_channel(name=f"入馆考核-{i.user.name}", overwrites=overwrites, category=i.channel.category)
        
        embed = discord.Embed(title="🔞 满血猫咖·核心成员入馆考核", color=0x000000)
        embed.description = (
            f"您好 {i.user.mention}，入馆前请在本频道内按要求完成考核：\n\n"
            "**一、年龄与身份证明**\n"
            "1. 请发送【支付宝-我的-个人信息】截图（需清晰显示20+年龄）。\n\n"
            "**二、专业考核题 (请直接回复编号并作答)：**\n"
            "1. **关于倒卖**：如果发现有人在社区内推荐“资源贩子”或倒卖免费角色卡，你的正确做法是？\n"
            "2. **版权红线**：社区规则严禁“二传、二改”。你如何看待将社区免费卡搬运到套壳付费APP（如XX镜像站、XX对话软件）的行为？\n"
            "3. **酒馆AI常识**：简述 SillyTavern（酒馆）前端与 AI 模型（API）之间的关系。为什么我们强调禁止分享包含私密 Key 的 JSON 文件？\n"
            "4. **行为规范**：对于社区内的引战、谩骂或恶意刷屏，你是否承诺绝对遵守文明交流协议？\n\n"
            "**完成后请艾特管理员。馆长或店长将进行人工终审！**"
        )
        embed.set_footer(text="馆长寄语：尊重原创，共建纯粹的 AI 交流环境。")
        await ch.send(embed=embed, view=AdultReviewView(i.user))
        await i.response.send_message(f"✅ 考核频道已开启：{ch.mention}\n请进入频道开始答题喵！", ephemeral=True)

# ======================================================
# --- 3. 核心：发卡 (任何人可为自己的作品加密) ---
# ======================================================
class PasswordInputModal(Modal, title='🐱 猫猫管家：安全验证'):
    input_val = TextInput(label='请输入暗号', placeholder='验证通过后发资源...', required=True)
    def __init__(self, correct_pwd, files, needs_extra=None):
        super().__init__()
        self.correct_pwd, self.files, self.needs_extra = correct_pwd, files, needs_extra
    async def on_submit(self, interaction: discord.Interaction):
        if self.needs_extra == "reaction":
            try:
                starter = await interaction.channel.fetch_message(interaction.channel.id)
                if not any(interaction.user.id in [u.id async for u in r.users()] for r in starter.reactions):
                    return await interaction.response.send_message("❌ 暗号对了，但你还没给首楼【添加反应】喵！", ephemeral=True)
            except: pass
        if self.input_val.value == self.correct_pwd:
            try: await interaction.user.send(f"🐱 资源已发：\n" + "\n".join(self.files))
            except: await interaction.response.send_message(f"✅ 验证成功：\n" + "\n".join(self.files), ephemeral=True)
        else: await interaction.response.send_message("❌ 暗号不对喵！", ephemeral=True)

class ProtectModal(Modal):
    def __init__(self, mode, files):
        super().__init__(title=f"猫猫上传 - {mode}")
        self.mode, self.files = mode, files
    desc = TextInput(label='描述', style=discord.TextStyle.paragraph, required=False)
    pwd_setting = TextInput(label='设置暗号', placeholder='口令模式必填...', required=False)
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🔒 受保护的附件", color=0x2ecc71)
        tips = {"口令模式": "🔑 输口令", "反应模式": "👍 给首楼反应", "评论模式": "💬 帖内评论", "反应+口令": "👍🔑 反应+口令", "反应+评论": "👍💬 反应并评论"}
        embed.add_field(name="💡 条件", value=tips.get(self.mode, "验证"), inline=False)
        await interaction.response.send_message(embed=embed, view=VerifyView(self.mode, self.files, self.pwd_setting.value))

class VerifyView(View):
    def __init__(self, mode, files, correct_pwd):
        super().__init__(timeout=None)
        self.mode, self.files, self.correct_pwd = mode, files, correct_pwd
    @discord.ui.button(label="验证获取附件", style=discord.ButtonStyle.success, emoji="✅")
    async def verify(self, interaction: discord.Interaction, button: Button):
        if "口令" in self.mode: return await interaction.response.send_modal(PasswordInputModal(self.correct_pwd, self.files, "reaction" if "反应" in self.mode else None))
        await interaction.response.defer(ephemeral=True)
        try:
            starter = await interaction.channel.fetch_message(interaction.channel.id)
            has_r = any(interaction.user.id in [u.id async for u in r.users()] for r in starter.reactions)
            has_c = False
            if "评论" in self.mode:
                async for m in interaction.channel.history(limit=50):
                    if m.author.id == interaction.user.id and m.id != starter.id: has_c = True; break
            if (self.mode=="反应模式" and has_r) or (self.mode=="评论模式" and has_c) or (self.mode=="反应+评论" and has_r and has_c):
                await interaction.followup.send("✅ 验证通过：\n" + "\n".join(self.files), ephemeral=True)
            else: await interaction.followup.send("❌ 条件未达成喵！", ephemeral=True)
        except: await interaction.followup.send("❌ 出错喵！", ephemeral=True)

# ======================================================
# --- 4. 核心：身份认证中心 & 投诉系统 ---
# ======================================================
class IdentityApplyModal(Modal):
    def __init__(self, role):
        super().__init__(title=f"申请【{role}】")
        self.role = role
    link = TextInput(label='作品链接', required=True)
    async def on_submit(self, i):
        try:
            parts = self.link.value.split('/')
            msg = await i.client.get_channel(int(parts[-2])).fetch_message(int(parts[-1]))
            if msg.author.id == i.user.id and sum(r.count for r in msg.reactions) >= 5:
                r_obj = discord.utils.get(i.guild.roles, name=self.role)
                await i.user.add_roles(r_obj)
                await i.response.send_message(f"🎉 认证成功！获得【{self.role}】", ephemeral=True)
            else: await i.response.send_message("❌ 条件不满足喵！", ephemeral=True)
        except: await i.response.send_message("❌ 链接无效喵！", ephemeral=True)

class IdentityCenterView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="认证申请", style=discord.ButtonStyle.primary, emoji="✨", custom_id="id_center_btn")
    async def open(self, i, b):
        view = View()
        for r in ["创作者小猫", "维修小猫", "铲屎官", "做图小猫"]:
            btn = Button(label=r)
            async def mk(r=r):
                async def cb(it): await it.response.send_modal(IdentityApplyModal(r))
                return cb
            btn.callback = await mk()
            view.add_item(btn)
        await i.response.send_message("请选择：", view=view, ephemeral=True)

class ComplaintView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="创建投诉工单", style=discord.ButtonStyle.danger, emoji="🚨", custom_id="ticket_btn")
    async def ticket(self, i, b):
        overwrites = {i.guild.default_role: discord.PermissionOverwrite(read_messages=False), i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        ch = await i.guild.create_text_channel(name=f"投诉-{i.user.name}", overwrites=overwrites, category=i.channel.category)
        await ch.send(f"🐱 {i.user.mention} 请提交您的投诉/举报内容，并附带截图证据。")
        await i.response.send_message(f"✅ 工单已开：{ch.mention}", ephemeral=True)

# ======================================================
# --- 5. 机器人主体与权限限定指令 ---
# ======================================================
class MaomaoBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members, intents.reactions, intents.message_content = True, True, True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
    async def setup_hook(self):
        self.add_view(AdultApplyView()); self.add_view(IdentityCenterView()); self.add_view(ComplaintView())
        await self.tree.sync()

bot = MaomaoBot()

@bot.tree.command(name="受保护附件")
async def protect_file(i: discord.Interaction, 附件1: discord.Attachment, 附件2: discord.Attachment=None):
    files = [f.url for f in [附件1, 附件2] if f]
    view = View()
    for m in ["口令模式", "反应模式", "评论模式", "反应+口令", "反应+评论"]:
        btn = Button(label=m, style=discord.ButtonStyle.primary)
        async def mk(m=m):
            async def cb(it): await it.response.send_modal(ProtectModal(m, files))
            return cb
        btn.callback = await mk()
        view.add_item(btn)
    await i.response.send_message("⚙️ 选择发卡模式：", view=view, ephemeral=True)

@bot.tree.command(name="删除帖子")
async def del_t(i: discord.Interaction):
    if not isinstance(i.channel, discord.Thread): return await i.response.send_message("❌ 非帖子频道喵！", ephemeral=True)
    if i.user.guild_permissions.administrator or i.channel.owner_id == i.user.id:
        await i.channel.delete()
    else: await i.response.send_message("❌ 只有管理或本人能删帖喵！", ephemeral=True)

@bot.tree.command(name="删除消息")
async def del_m(i: discord.Interaction, 链接: str):
    try:
        msg = await i.channel.fetch_message(int(链接.split('/')[-1]))
        if i.user.guild_permissions.administrator or msg.author.id == i.user.id:
            await msg.delete(); await i.response.send_message("✅ 已爆破！", ephemeral=True)
        else: await i.response.send_message("❌ 只有管理或本人能删消息喵！", ephemeral=True)
    except: await i.response.send_message("❌ 消息不存在喵！", ephemeral=True)

@bot.tree.command(name="初始化成人验证")
@app_commands.default_permissions(administrator=True)
async def init_a(i): await i.response.send_message("🔞 成人认证中心", view=AdultApplyView())

@bot.tree.command(name="发送投诉面板")
@app_commands.default_permissions(administrator=True)
async def init_c(i): await i.response.send_message("🚨 投诉沟通系统", view=ComplaintView())

@bot.tree.command(name="发送认证中心")
@app_commands.default_permissions(administrator=True)
async def init_id(i): await i.response.send_message("✨ 创作者认证中心", view=IdentityCenterView())

@bot.tree.command(name="封禁公示")
@app_commands.default_permissions(administrator=True)
async def ban(i, 用户: discord.Member, 理由: str):
    await i.response.send_message(embed=discord.Embed(title="⚖️ 封禁公示", description=f"用户：{用户.mention}\n理由：{理由}", color=0x992d22))

@bot.tree.command(name="回顶")
async def go_t(i):
    async for m in i.channel.history(limit=1, oldest_first=True): await i.response.send_message(f"📌 [跳回首楼]({m.jump_url})", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
