import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from flask import Flask
import threading
import os

# --- 1. 网页保活 ---
app = Flask('')
@app.route('/')
def home(): return "猫猫管家：修复了首楼识别逻辑喵！🐾"

# --- 2. 交互逻辑：暗号验证弹窗 ---
class PasswordInputModal(Modal, title='🐱 猫猫管家：安全验证'):
    input_val = TextInput(label='请输入暗号', placeholder='暗号正确才会发资源给你喵...', required=True)
    def __init__(self, correct_pwd, files, needs_extra=None):
        super().__init__()
        self.correct_pwd = correct_pwd
        self.files = files
        self.needs_extra = needs_extra

    async def on_submit(self, interaction: discord.Interaction):
        # 混合模式下，输完暗号还要二次检查点赞
        if self.needs_extra == "like":
            try:
                # 抓取首楼（帖子的 ID 就是第一条消息的 ID）
                starter_msg = await interaction.channel.fetch_message(interaction.channel.id)
                liked = any(interaction.user.id in [u.id async for u in r.users()] for r in starter_msg.reactions if str(r.emoji) in ["👍", "❤️", "✅", "🔥"])
                if not liked:
                    return await interaction.response.send_message("❌ 暗号对了，但你还没给首楼【点赞】喵！", ephemeral=True)
            except:
                pass

        if self.input_val.value == self.correct_pwd:
            try:
                file_links = "\n".join(self.files)
                await interaction.user.send(f"🐱 **这是馆长托我发你的资源：**\n{file_links}")
                await interaction.response.send_message("✅ 验证成功！资源已私发喵！", ephemeral=True)
            except:
                await interaction.response.send_message(f"✅ 验证成功！但私信发不了，直接给你：\n" + "\n".join(self.files), ephemeral=True)
        else:
            await interaction.response.send_message("❌ 暗号不对喵！", ephemeral=True)

# --- 3. 核心：上传表单 (保持馆长最爱的样式) ---
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

# --- 4. 验证逻辑 (重构了首楼抓取逻辑) ---
class VerifyView(View):
    def __init__(self, mode, files, correct_pwd):
        super().__init__(timeout=None)
        self.mode = mode
        self.files = files
        self.correct_pwd = correct_pwd

    @discord.ui.button(label="验证并获取附件", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 情况 A：涉及口令
        if self.mode == "口令模式":
            return await interaction.response.send_modal(PasswordInputModal(self.correct_pwd, self.files))
        if self.mode == "点赞+口令模式":
            return await interaction.response.send_modal(PasswordInputModal(self.correct_pwd, self.files, needs_extra="like"))

        await interaction.response.defer(ephemeral=True)
        
        try:
            # 【核心修复】更加鲁棒的首楼抓取逻辑
            target_id = interaction.channel.id
            starter_msg = None
            
            # 尝试直接获取
            try:
                starter_msg = await interaction.channel.fetch_message(target_id)
            except:
                # 备用方案：翻阅历史记录的第一条
                async for m in interaction.channel.history(limit=1, oldest_first=True):
                    starter_msg = m

            if not starter_msg:
                return await interaction.followup.send("❌ 无法识别首楼信息，请联系管理员喵！", ephemeral=True)

            user_id = interaction.user.id
            
            # 1. 检查点赞 (👍 ❤️ ✅ 🔥 🆗)
            liked = False
            for r in starter_msg.reactions:
                if str(r.emoji) in ["👍", "❤️", "✅", "🔥", "🆗", "⭐"]:
                    users = [u.id async for u in r.users()]
                    if user_id in users:
                        liked = True
                        break
            
            # 2. 检查评论
            commented = False
            if "评论" in self.mode:
                async for m in interaction.channel.history(limit=50):
                    if m.author.id == user_id and m.id != starter_msg.id:
                        commented = True
                        break

            # 3. 验证通过判断
            can_pass = False
            if self.mode == "点赞模式": can_pass = liked
            elif self.mode == "评论模式": can_pass = commented
            elif self.mode == "点赞+评论模式": can_pass = (liked and commented)

            if can_pass:
                links = "\n".join(self.files)
                try:
                    await interaction.user.send(f"🐱 **这是馆长托我发你的资源：**\n{links}")
                    await interaction.followup.send("✅ 验证通过！资源已私发喵！", ephemeral=True)
                except:
                    await interaction.followup.send(f"✅ 验证通过！但无法私信，直接发这：\n{links}", ephemeral=True)
            else:
                fail_msg = "你还没给首楼点赞哦喵！" if not liked else "你还没发表评论哦喵！"
                if "点赞+评论" in self.mode and (not liked or not commented):
                    fail_msg = "点赞和评论都要完成才可以喵！"
                await interaction.followup.send(f"❌ {fail_msg}", ephemeral=True)
                
        except Exception as e:
            print(f"Error detail: {e}")
            await interaction.followup.send(f"❌ 验证过程中出了点小状况，请稍后再试喵！", ephemeral=True)

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

# 【删除消息/回顶指令保持原样】
@bot.tree.command(name="删除消息")
async def del_msg(interaction: discord.Interaction, 链接: str):
    try:
        mid = int(链接.split('/')[-1])
        msg = await interaction.channel.fetch_message(mid)
        await msg.delete()
        await interaction.response.send_message("✅ 消息已爆破！", ephemeral=True)
    except: await interaction.response.send_message("❌ 链接无效喵！", ephemeral=True)

@bot.tree.command(name="回顶")
async def go_top(interaction: discord.Interaction):
    async for m in interaction.channel.history(limit=1, oldest_first=True):
        embed = discord.Embed(title="📌 频道第一条消息", color=0x3498db, description=f"**内容**: {m.content[:100]}\n\n[点击跳转]({m.jump_url})")
        await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
