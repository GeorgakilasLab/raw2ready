"""Theme configuration module.

Provides reusable UI theme layouts, brand names, and color palettes
loaded from the central configuration YAML file.
"""

import src.utils.tools as tools

from contextlib import contextmanager
from nicegui import ui
from nicegui.element import Element
from src.utils.fonts_ import font_header, title, subheader, body_text


configuration_filepath = './src/config/config.yaml'
config_content, config_content_dump = tools.load_config(configuration_filepath)


# ----------------------
# Base colors:
# ----------------------
colors_ = {
    'primary': {
        'value': config_content['theme_settings']['color_primary']['value'],
        'description': config_content['theme_settings']['color_primary']['description']
    },

    'secondary': {
        'value': config_content['theme_settings']['color_secondary']['value'],
        'description': config_content['theme_settings']['color_secondary']['description']
    },

    'accent': {
        'value': config_content['theme_settings']['color_accent']['value'],
        'description': config_content['theme_settings']['color_accent']['description']
    },

    'positive': {
        'value': config_content['theme_settings']['color_positive']['value'],
        'description': config_content['theme_settings']['color_positive']['description']
    },
}


# --------------------
# Names
# --------------------
themes_ = {
    'software_name_': config_content['general_settings']['software_name'],
    'header_text': config_content['theme_settings']['header']['header_text'],
    'funding_logo': config_content['general_settings']['funding_logo'],

    'funding_logo_size': (
        f"w-{config_content['theme_settings']['footer']['footer_funding_logo_width']} "
        f"h-{config_content['theme_settings']['footer']['footer_funding_logo_height']}"
    ),

    # 'organisation_logo': config_content['general_settings']['organisation_logo'],
    # 'organisation_logo_size': (
    #     f"w-{config_content['theme_settings']['footer']['footer_organisation_logo_width']} "
    #     f"h-{config_content['theme_settings']['footer']['footer_organisation_logo_height']}"
    # ),
}


# -----------------------
# FUNCTIONS
# -----------------------
@contextmanager
def frame(navigation_title: str):
    """Custom page frame context manager to share header/footer style.

    Args:
        navigation_title: Title append text for the header label.
    """

    ui.colors(
        primary=colors_['primary']['value'],
        secondary=colors_['secondary']['value'],
        accent=colors_['accent']['value'],
        positive=colors_['positive']['value']
    )

    if themes_['header_text']:
        with ui.header():
            with ui.row():
                font_header(themes_['software_name_'] + navigation_title)

    with ui.column().classes('w-full'):
        yield

        # with ui.row():
        #     ui.space()
        #     ui.image(themes_['organisation_logo']) \
        #         .props('fit=scale-down') \
        #         .classes(themes_['organisation_logo_size']) \
        #         .style('height: 50px')