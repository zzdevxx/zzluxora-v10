"""
about_panel.py | Academic Thesis Information & Software Credentials Dialog
Presents official student credentials, advisor information, UNNES affiliation, and research title.
"""

from __future__ import annotations
from pathlib import Path

from ui.qt_compat import (
    HAS_QT, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QPixmap, QIcon, Qt
)
from ui.styles import Theme, CONSOLE_QSS


class AboutDialog(QDialog if HAS_QT else object):
    """About Dialog: Academic Thesis Metadata & Software Credentials."""
    def __init__(self, parent: QWidget | None = None):
        if not HAS_QT: return
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle("About")
        self.resize(720, 560)
        self.setStyleSheet(CONSOLE_QSS)

        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo_zz.png"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(12)

        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo_zz.png"

        # Header Row (Official Logo Badge + Title)
        header_row = QHBoxLayout()
        header_row.setSpacing(14)
        if logo_path.exists():
            logo_lbl = QLabel()
            pix = QPixmap(str(logo_path)).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            logo_lbl.setFixedSize(48, 48)
            logo_lbl.setStyleSheet("border-radius: 4px; background: transparent;")
            header_row.addWidget(logo_lbl)

        title_box = QVBoxLayout()
        title = QLabel("ZZLUXORA v10")
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {Theme.TEXT_PRIMARY};")
        subtitle = QLabel("Intelligent Audio-Reactive Stage Lighting Controller | Computer Engineering FT UNNES")
        subtitle.setStyleSheet(f"font-size: 11px; color: {Theme.ACCENT_CYAN};")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        # Scrollable Content Card for spacious readability
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {Theme.BORDER_STRONG};
                border-radius: 6px;
                background-color: {Theme.BG_SURFACE};
            }}
        """)

        card = QWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        fields = [
            ("Application", "ZZLUXORA (v10.0.0 Next-Gen Production Stage Console)"),
            ("Description", "Audio-Reactive Stage Lighting Design System based on Worship Music Mood Analysis with HSV-RGBW Color Mapping and Art-Net DMX512 Protocol."),
            ("Researcher", "Andreas Restuawanta Christwara"),
            ("Student ID (NIM)", "5312422036"),
            ("Study Program", "S1 Teknik Komputer (Computer Engineering)"),
            ("Department", "Teknik Elektro (Electrical Engineering)"),
            ("Faculty", "Fakultas Teknik (Faculty of Engineering)"),
            ("University", "Universitas Negeri Semarang (UNNES)"),
            ("Thesis Advisor", "Mario Norman Syah, S.Pd., M.Eng."),
            ("Research Title", "Rancang Bangun Sistem Audio-Reactive Lighting Design Berbasis Analisis Mood Lagu Rohani dengan Pemetaan Warna HSV-RGBW dan Protokol Art-Net DMX512"),
            ("Field Location", "Gereja Isa Almasih (GIA) Deliksari, Kota Semarang"),
        ]

        for label_text, val_text in fields:
            row = QHBoxLayout()
            row.setSpacing(12)
            lbl = QLabel(label_text + ":")
            lbl.setFixedWidth(135)
            lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            lbl.setStyleSheet(f"font-weight: 700; color: {Theme.TEXT_SECONDARY}; font-size: 12px;")

            val = QLabel(val_text)
            val.setWordWrap(True)
            val.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; font-size: 12px; line-height: 1.4;")

            row.addWidget(lbl)
            row.addWidget(val, 1)
            card_layout.addLayout(row)

        card_layout.addStretch()
        scroll.setWidget(card)
        main_layout.addWidget(scroll, 1)

        # Bottom Close Button
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("min-width: 80px; padding: 6px 14px; border-radius: 4px;")
        btn_close.clicked.connect(self.close)
        btn_bar.addWidget(btn_close)
        main_layout.addLayout(btn_bar)
