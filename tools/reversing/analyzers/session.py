from types import TracebackType
from typing import Any

import r2pipe


class R2Session:
    def __init__(self, sample: str, log_level: int = 0) -> None:
        self.sample: str = sample
        self.log_level: int = log_level
        self.r2: Any | None = None


    def __enter__(self) -> Any:
        self.r2 = r2pipe.open(self.sample, flags=["-e", "bin.relocs.apply=true"])

        # 0=silent, 1=error, 2=warning, 3=info, 4=debug
        self.r2.cmd(f"e log.level={self.log_level}")

        self.r2.cmd("aaa")
        return self.r2


    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.r2:
            self.r2.quit()
