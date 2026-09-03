from types import SimpleNamespace

from wms import loading


class FakePlaceholder:
    def __init__(self):
        self.payload = ""
        self.unsafe_allow_html = False
        self.empty_calls = 0

    def markdown(self, payload, unsafe_allow_html=False):
        self.payload = payload
        self.unsafe_allow_html = unsafe_allow_html

    def empty(self):
        self.empty_calls += 1


def test_loading_screen_escapes_text_and_is_accessible(monkeypatch):
    placeholder = FakePlaceholder()
    monkeypatch.setattr(
        loading,
        "st",
        SimpleNamespace(empty=lambda: placeholder),
    )

    returned = loading.show_loading_screen(
        "Membuka <Mirai>",
        'Pesan "aman" & cepat',
    )

    assert returned is placeholder
    assert placeholder.unsafe_allow_html is True
    assert "Membuka &lt;Mirai&gt;" in placeholder.payload
    assert "Pesan &quot;aman&quot; &amp; cepat" in placeholder.payload
    assert 'role="status"' in placeholder.payload
    assert "prefers-reduced-motion" in placeholder.payload


def test_hide_loading_screen_accepts_placeholder_or_none():
    placeholder = FakePlaceholder()

    loading.hide_loading_screen(placeholder)
    loading.hide_loading_screen(None)

    assert placeholder.empty_calls == 1
