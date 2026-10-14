"""Fake Playwright page/locator untuk menguji alur upload tanpa browser."""

from __future__ import annotations

from typing import Any


class FakeLocator:
    def __init__(self, page: "FakePage", selector: str):
        self.page = page
        self.selector = selector

    @property
    def first(self) -> "FakeLocator":
        return self

    def nth(self, index: int) -> "FakeLocator":
        return self

    def all(self) -> list["FakeLocator"]:
        return []

    def is_visible(self, timeout: int | None = None) -> bool:
        return False

    def is_checked(self) -> bool:
        return False

    def click(self, *args: Any, **kwargs: Any) -> None:
        self.page.actions.append(("click", self.selector))

    def set_input_files(self, files: Any) -> None:
        self.page.actions.append(("set_input_files", files))

    def wait_for(self, state: str | None = None, timeout: int | None = None) -> None:
        return None

    def press(self, key: str) -> None:
        self.page.actions.append(("press", key))

    def press_sequentially(self, text: str, delay: int | None = None) -> None:
        self.page.actions.append(("type", text))

    def get_attribute(self, name: str) -> str | None:
        if name == "data-disabled":
            return "false"
        return None

    def scroll_into_view_if_needed(self) -> None:
        return None

    def inner_text(self) -> str:
        return ""


class FakePage:
    def __init__(self, url: str = "https://www.tiktok.com/tiktokstudio/upload"):
        self.url = url
        self.actions: list[tuple] = []
        self.context = None

    def goto(self, url: str, wait_until: str | None = None) -> None:
        self.url = url
        self.actions.append(("goto", url))

    def wait_for_selector(
        self, selector: str, state: str | None = None, timeout: int | None = None
    ) -> FakeLocator:
        return FakeLocator(self, selector)

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    def evaluate(self, script: str) -> None:
        return None
