from pathlib import Path

from core.ai.runtime.inference.memory import InferenceMemory


DEFAULT_DYNAMIC_INFERENCE_FLUSH_INTERVAL = 5


class DynamicInferenceMemory(InferenceMemory):
    def __init__(
        self,
        output_dir: str | Path,
        filename: str,
        name: str,
        flush_interval: int = DEFAULT_DYNAMIC_INFERENCE_FLUSH_INTERVAL,
    ) -> None:
        super().__init__(
            output_dir=output_dir,
            filename=filename,
            name=name,
            flush_interval=flush_interval,
        )
