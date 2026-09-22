"""Page views for the top-navbar app (registered by app.py via st.navigation).
Each is a plain function that reads the signed-in user from st.session_state."""
from .home import home
from .projects import projects
from .calendar import calendar_view
from .team import team
from .account import account

__all__ = ["home", "projects", "calendar_view", "team", "account"]
