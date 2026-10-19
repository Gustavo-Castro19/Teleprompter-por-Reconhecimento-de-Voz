class ScriptAligner:
    def __init__(self, spoken_to_visual_map: list[int], visual_lines: list[str]):
        self.spoken_to_visual = spoken_to_visual_map
        self.visual_lines = visual_lines

    def get_visual_index(self, spoken_index: int) -> int:
        if spoken_index < len(self.spoken_to_visual):
            return self.spoken_to_visual[spoken_index]
        return len(self.visual_lines) - 1

    def get_first_visual_index(self) -> int:
        return self.spoken_to_visual[0] if self.spoken_to_visual else 0