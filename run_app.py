"""Web application entry point for raw2ready.

Starts the NiceGUI-based web user interface for parsing, merging, and
analyzing bioreactor data.
"""

# --------------------------------------------------
# PACKAGES
# --------------------------------------------------
import os
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.utils.paths import ensure_dirs

from nicegui import ui, app

import src.utils.tools as tools
import src.utils.logging_config as logging_config
# from tools.auth_service import auth

import src.gui.main_page as main_page
# import src.gui.database_admin as database_admin
# import src.gui.login_gui as login_gui
# import src.gui.register_gui as register_gui
# import src.gui.admin_users as admin_users


# --------------------------------------------------
# VARIABLES
# --------------------------------------------------
DIRS = ensure_dirs()
app.storage.general["DIRS"] = { k:str(v) for k, v in DIRS.items()}

BASE_DIR = Path(__file__).resolve().parent

print("DIRS:", DIRS)

configuration_filepath = str(
    BASE_DIR / "config" / "config.yaml"
)

assets_path = BASE_DIR / "assets"


# --------------------------------------------------
# AUTH HELPERS
# --------------------------------------------------
#def is_logged_in() -> bool:
#    return auth.is_logged_in()


#def user_role() -> str:
#    return str(
#        auth.current_user().get("role", "")
#    ).lower()


#def require_login():

#    if not is_logged_in():
#        ui.navigate.to("/login")
#        return False

#    return True


#def require_admin():

#    if not is_logged_in():
#        ui.navigate.to("/login")
#        return False

#    role = user_role()

#    if role not in [
#        "admin",
#        "superadmin",
#    ]:
#        ui.notify(
#            "Admin access required",
#            type="negative",
#        )
#        ui.navigate.to("/")
#        return False

#    return True


# --------------------------------------------------
# MAIN
# --------------------------------------------------
if __name__ in {
    "__main__",
    "__mp_main__",
}:

    print(configuration_filepath)

    # ---------------------------------
    # Initialize logging
    # ---------------------------------
    logger = logging_config.setup_logging(
        log_level=logging.INFO,
        console_logging=True,
    )

    logger.info(
        "Logging system initialized"
    )

    logger.info(
        "Starting Raw2Ready Application"
    )

    # ---------------------------------
    # Clean runtime memory on startup
    # ---------------------------------
    app.storage.general.clear()
    app.storage.general["DIRS"] = { k:str(v) for k, v in DIRS.items()}

    logger.info(
        "Runtime storage cleared"
    )

    # ---------------------------------
    # Log output directory
    # ---------------------------------
    logger.info(
        f"Output directory: "
        f"{DIRS['base']}"
    )

    # ---------------------------------
    # Load config
    # ---------------------------------
    config_content, config_content_dump = (
        tools.load_config(
            configuration_filepath
        )
    )

    logger.info(
        "Configuration loaded successfully"
    )

    # ---------------------------------
    # Register static assets
    # ---------------------------------
    if assets_path.exists():

        app.add_static_files(
            "/assets",
            str(assets_path),
        )

        logger.info(
            f"Assets mounted: "
            f"{assets_path}"
        )

    else:

        logger.warning(
            f"Assets folder not found: "
            f"{assets_path}"
        )

    # ---------------------------------
    # Register temp charts folder
    # ---------------------------------
    app.add_static_files(
        "/temp_charts",
        str(DIRS["charts"]),
    )

    logger.info(
        f"Temp charts mounted: "
        f"{DIRS['charts']}"
    )

    # ---------------------------------
    # PUBLIC ROUTES
    # ---------------------------------
    logger.info(
        "Initializing public pages"
    )

  #  login_gui.LoginPage(
  #      page_url="/login",
  #      add_page=True,
  #  )

  #  register_gui.RegisterPage(
  #      page_url="/register",
  #      add_page=True,
  #  )

    @ui.page("/logout")
    def logout_page():
        """Logs out the current user and redirects to the login page."""

        auth.logout_user()

        ui.notify(
            "Logged out successfully",
            type="info",
        )

        ui.navigate.to("/login")

    logger.info(
        "Login/Register pages initialized"
    )

    # ---------------------------------
    # PROTECTED MAIN PAGE
    # ---------------------------------
    logger.info(
        "Initializing protected pages"
    )

    @ui.page("/")
    async def protected_home():
        """Renders the main page of the application.

        If RAW2READY_OUTPUT_DIR is not yet configured, shows a
        first-launch setup dialog before rendering the main page.
        """

#        if not require_login():
#            return

        # ---------------------------------
        # First-launch output dir setup
        # ---------------------------------
        if not os.environ.get("RAW2READY_OUTPUT_DIR"):
            await show_output_dir_setup()
            return

        page = main_page.main_page(
            config=config_content,
            page_url_path="/",
            frame_name="Raw2Ready",
            add_page=False,
            dirs=DIRS,
        )

        # uses runtime rendering
        if hasattr(page, "add_page_runtime"):
            await page.add_page_runtime()
        else:
            page.content_()

    logger.info(
        "Main page initialized: /"
    )

    # ---------------------------------
    # ADMIN DATABASE PAGE
    # ---------------------------------
    @ui.page("/admin/db")
    def protected_database():
        """Renders the protected database administration page."""

        if not require_admin():
            return

        page = database_admin.DatabaseAdmin(
            config=config_content,
            page_url_path="/admin/db",
            frame_name="Database Admin",
            add_page=False,
            storage_container={"DIRS": DIRS},
        )

        page.content_()

    logger.info(
        "Database page initialized: /admin/db"
    )

    # ---------------------------------
    # ADMIN USERS PAGE
    # ---------------------------------
    @ui.page("/admin/users")
    def protected_admin_users():
        """Renders the protected user administration page."""

        if not require_admin():
            return

        page = admin_users.AdminUsersPage(
            config=config_content,
            page_url="/admin/users",
            frame_name="User Administration",
            add_page=False,
            storage_container={"DIRS": DIRS},
        )

        page.content_()

    logger.info(
        "Users page initialized: /admin/users"
    )

    logger.info(
        "All pages initialized successfully"
    )

    # ---------------------------------
    # RUN APP
    # ---------------------------------
    logger.info(
        "Starting web server"
    )

    ui.run(
        title=config_content[
            "general_settings"
        ]["app_title"],

        host="0.0.0.0",
        port=8081,

        storage_secret="raw2ready_secret_key",

        reload=False,

        reconnect_timeout=60,

        favicon="assets/images/project_logo.jpg",
    )


# --------------------------------------------------
# FIRST-LAUNCH SETUP DIALOG
# --------------------------------------------------
async def show_output_dir_setup():
    """Displays a first-launch dialog for the user to set the output directory.

    Writes the chosen path to a .env file and reloads the page.
    """

    default_path = str(Path.home() / ".raw2ready")

    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Welcome to Raw2Ready").classes(
            "text-xl font-bold"
        )
        ui.label(
            "Please specify a directory where all output "
            "files (reports, exports, charts, logs) will be saved."
        ).classes("text-sm text-gray-600")

        path_input = ui.input(
            label="Output Directory",
            value=default_path,
        ).classes("w-full")

        async def save_and_reload():
            """Persists the chosen path to .env and reloads."""

            chosen = path_input.value.strip()

            if not chosen:
                ui.notify(
                    "Please enter a valid path",
                    type="warning",
                )
                return

            env_path = Path(__file__).resolve().parent / ".env"

            lines = []
            if env_path.exists():
                lines = env_path.read_text().splitlines()

            # Remove any existing RAW2READY_OUTPUT_DIR line
            lines = [
                ln for ln in lines
                if not ln.startswith("RAW2READY_OUTPUT_DIR=")
            ]
            lines.append(f"RAW2READY_OUTPUT_DIR={chosen}")

            env_path.write_text("\n".join(lines) + "\n")

            os.environ["RAW2READY_OUTPUT_DIR"] = chosen

            # Re-initialize directories
            global DIRS
            DIRS = ensure_dirs()
            app.storage.general["DIRS"] = {
                k: str(v) for k, v in DIRS.items()
            }

            dialog.close()

            ui.notify(
                f"Output directory set to: {chosen}",
                type="positive",
            )

            ui.navigate.to("/")

        ui.button(
            "Save & Continue",
            on_click=save_and_reload,
        ).classes("w-full mt-2")

    dialog.open()
    await dialog