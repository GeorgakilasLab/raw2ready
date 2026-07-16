"""Fonts configuration module.

Defines a set of reusable typography subclasses extending NiceGUI's ui.label.
"""

from nicegui import ui


class font_header(ui.label):
    """Header text label with white bold styling."""

    def __init__(self, text: str) -> None:
        """Initializes font_header.

        Args:
            text: Text to display.
        """
        super().__init__(text)
        self.classes('text-h5 text-white-8 font-bold')


class title(ui.label):
    """Title text label with large grey bold styling."""

    def __init__(self, text: str) -> None:
        """Initializes title.

        Args:
            text: Text to display.
        """
        super().__init__(text)
        self.classes('text-h2 text-grey-8 font-bold')


class subheader(ui.label):
    """Subheader text label with medium grey styling."""

    def __init__(self, text: str) -> None:
        """Initializes subheader.

        Args:
            text: Text to display.
        """
        super().__init__(text)
        self.classes('text-h4 text-grey-8')


class body_text(ui.label):
    """Body text label with custom grey text colors."""

    def __init__(self, text: str, text_color_ = 'grey-6'):
        """Initializes body_text.

        Args:
            text: Text to display.
            text_color_: CSS/Quasar color name suffix. Defaults to 'grey-6'.
        """
        super().__init__(text)
        text_props = 'text-h6 text-' + text_color_
        self.classes(text_props)


class label_text(ui.label):
    """Form label text with medium grey styling."""

    def __init__(self, text: str) -> None:
        """Initializes label_text.

        Args:
            text: Text to display.
        """
        super().__init__(text)
        self.classes('text-h5 text-grey-8')


class caption_text(ui.label):
    """Caption text label with small grey styling."""

    def __init__(self, text: str) -> None:
        """Initializes caption_text.

        Args:
            text: Text to display.
        """
        super().__init__(text)
        self.classes('text-h8 text-grey-6')


class about_text(ui.label):
    """About-section body description label."""

    def __init__(self, text: str) -> None:
        """Initializes about_text.

        Args:
            text: Text to display.
        """
        super().__init__(text)
        self.classes('text-h6 text-grey-6')


class preview_text(ui.label):
    """Preview metadata display label."""

    def __init__(self, text: str) -> None:
        """Initializes preview_text.

        Args:
            text: Text to display.
        """
        super().__init__(text)
        self.classes('text-h5 q-mb-md')