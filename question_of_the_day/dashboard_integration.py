from redbot.core import commands
from redbot.core.bot import Red
import discord
import typing
import wtforms
from wtforms import validators

def dashboard_page(*args, **kwargs):  # This decorator is required because the cog Dashboard may load after the third party when the bot is started.
    def decorator(func: typing.Callable):
        func.__dashboard_decorator_params__ = (args, kwargs)
        return func
    return decorator

class DashboardIntegration:
    bot: Red
    cog: commands.Cog

    def __init__(self, cog: commands.Cog):
        self.cog = cog

    @commands.Cog.listener()
    async def on_dashboard_cog_add(self, dashboard_cog: commands.Cog) -> None:  # ``on_dashboard_cog_add`` is triggered by the Dashboard cog automatically.
        dashboard_cog.rpc.third_parties_handler.add_third_party(self)  # Add the third party to Dashboard.

    @dashboard_page(name="manage_qotd_settings", description="Manage QOTD settings.", methods=("GET", "POST"), is_owner=True)
    async def manage_qotd_settings_page(self, user: discord.User, guild: discord.Guild, **kwargs) -> typing.Dict[str, typing.Any]:
        channels = [(channel.id, channel.name) for channel in guild.text_channels]

        class Form(kwargs["Form"]):
            def __init__(self):
                super().__init__(prefix="manage_qotd_settings_form_")
                self.qotd_channel.choices = channels

            qotd_channel: wtforms.SelectField = wtforms.SelectField("QOTD Channel:", validators=[validators.InputRequired()])
            qotd_time_hour: wtforms.IntegerField = wtforms.IntegerField("QOTD Time (Hour):", validators=[validators.InputRequired(), validators.NumberRange(min=0, max=23)])
            qotd_time_minute: wtforms.IntegerField = wtforms.IntegerField("QOTD Time (Minute):", validators=[validators.InputRequired(), validators.NumberRange(min=0, max=59)])
            submit: wtforms.SubmitField = wtforms.SubmitField("Update QOTD Settings")

        form: Form = Form()
        if form.validate_on_submit() and await form.validate_dpy_converters():
            channel_id = int(form.qotd_channel.data)
            qotd_time_hour = form.qotd_time_hour.data
            qotd_time_minute = form.qotd_time_minute.data
            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                return {
                    "status": 0,
                    "notifications": [{"message": "Invalid channel selected.", "category": "error"}],
                    "redirect_url": kwargs["request_url"],
                }

            await self.cog.config.guild(guild).post_in_channel.set(channel_id)
            await self.cog.config.guild(guild).post_at.set({"hour": qotd_time_hour, "minute": qotd_time_minute})
            await self.cog.update_guild_to_post_at(guild, qotd_time_hour, qotd_time_minute)
            return {
                "status": 0,
                "notifications": [{"message": f"QOTD settings updated successfully.", "category": "success"}],
                "redirect_url": kwargs["request_url"],
            }

        source = """
        <h3>Manage QOTD Settings</h3>
        <form method="post">
            {{ form.hidden_tag() }}
            <div class="form-group">
                {{ form.qotd_channel.label }} {{ form.qotd_channel(class="form-control") }}
            </div>
            <div class="form-group">
                {{ form.qotd_time_hour.label }} {{ form.qotd_time_hour(class="form-control") }}
            </div>
            <div class="form-group">
                {{ form.qotd_time_minute.label }} {{ form.qotd_time_minute(class="form-control") }}
            </div>
            <div class="form-group">
                {{ form.submit(class="btn btn-primary") }}
            </div>
        </form>
        """

        return {
            "status": 0,
            "web_content": {"source": source, "form": form},
        }

    @dashboard_page(name="manage_qotd_questions", description="Manage QOTD questions.", methods=("GET", "POST"), is_owner=True)
    async def manage_qotd_questions_page(self, user: discord.User, guild: discord.Guild, **kwargs) -> typing.Dict[str, typing.Any]:
        questions = await self.cog.config.guild(guild).questions()
        question_choices = [(str(i), q['question']) for i, q in enumerate(questions)]

        class Form(kwargs["Form"]):
            def __init__(self):
                super().__init__(prefix="manage_qotd_questions_form_")
                self.remove_question.choices = question_choices

            question: wtforms.StringField = wtforms.StringField("Question:", validators=[validators.Optional()])
            remove_question: wtforms.SelectField = wtforms.SelectField("Remove Question:", validators=[validators.Optional()])
            action: wtforms.SelectField = wtforms.SelectField("Action:", choices=[("add", "Add"), ("remove", "Remove")])
            submit: wtforms.SubmitField = wtforms.SubmitField("Update Questions")

        form: Form = Form()
        if form.validate_on_submit() and await form.validate_dpy_converters():
            question = form.question.data
            action = form.action.data
            remove_index = int(form.remove_question.data) if form.remove_question.data else None
            async with self.cog.config.guild(guild).questions() as questions:
                if action == "add":
                    if len(questions) >= MAX_QUESTIONS_PER_GUILD:
                        message = f"Error: too many questions already added in this server! Max is {MAX_QUESTIONS_PER_GUILD}."
                        category = "error"
                    else:
                        questions.append({"question": question, "asked_by": user.id})
                        message = f"Question added successfully."
                        category = "success"
                elif action == "remove":
                    if remove_index is not None and 0 <= remove_index < len(questions):
                        removed_question = questions.pop(remove_index)
                        message = f"Removed question: {removed_question['question']}"
                        category = "success"
                    else:
                        message = "Invalid question index."
                        category = "error"
            return {
                "status": 0,
                "notifications": [{"message": message, "category": category}],
                "redirect_url": kwargs["request_url"],
            }

        questions_list = '\n'.join([f"{i}. {q['question']}" for i, q in enumerate(questions)])

        source = f"""
        <h3>Manage QOTD Questions</h3>
        <h4>Current Questions:</h4>
        <pre>{questions_list}</pre>
        <form method="post">
            {{ form.hidden_tag() }}
            <div class="form-group">
                {{ form.question.label }} {{ form.question(class="form-control") }}
            </div>
            <div class="form-group">
                {{ form.remove_question.label }} {{ form.remove_question(class="form-control") }}
            </div>
            <div class="form-group">
                {{ form.action.label }} {{ form.action(class="form-control") }}
            </div>
            <div class="form-group">
                {{ form.submit(class="btn btn-primary") }}
            </div>
        </form>
        """

        return {
            "status": 0,
            "web_content": {"source": source, "form": form},
        }
