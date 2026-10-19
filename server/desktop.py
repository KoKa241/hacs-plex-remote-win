"""Validated desktop actions, independent of Plex focus or process state."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

SHORTCUTS = {
    "windows": (0x5B,),
    "escape": (0x1B,),
    "enter": (0x0D,),
    "backspace": (0x08,),
    "tab": (0x09,),
    "delete": (0x2E,),
    "alt_f4": (0x12, 0x73),
    "task_manager": (0x11, 0x10, 0x1B),
    "alt_tab": (0x12, 0x09),
    "show_desktop": (0x5B, 0x44),
    "select_all": (0x11, 0x41),
    "copy": (0x11, 0x43),
    "paste": (0x11, 0x56),
}


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Move(Action):
    kind: Literal["move"]
    dx: int = Field(ge=-500, le=500)
    dy: int = Field(ge=-500, le=500)


class Click(Action):
    kind: Literal["click"]
    button: Literal["left", "right"]


class Scroll(Action):
    kind: Literal["scroll"]
    steps: int = Field(ge=-10, le=10)


class Text(Action):
    kind: Literal["text"]
    text: str = Field(min_length=1, max_length=2000)


class Shortcut(Action):
    kind: Literal["shortcut"]
    key: Literal[
        "windows",
        "escape",
        "enter",
        "backspace",
        "tab",
        "delete",
        "alt_f4",
        "task_manager",
        "alt_tab",
        "show_desktop",
        "select_all",
        "copy",
        "paste",
    ]


DesktopAction = Annotated[Move | Click | Scroll | Text | Shortcut, Field(discriminator="kind")]
ACTION_ADAPTER = TypeAdapter(DesktopAction)
