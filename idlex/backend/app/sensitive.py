"""敏感词 DFA 过滤（开发环境运行时从 DB 词库 + 内置词表构建）"""
BUILTIN_WORDS = ["诈骗", "赌博", "代购刷单", "色情", "违禁品", "假货", "办证", "枪支"]


class DFAFilter:
    def __init__(self):
        self.root = {}
        self._load(BUILTIN_WORDS)

    def _load(self, words):
        for word in words:
            w = word.strip()
            if not w:
                continue
            node = self.root
            for ch in w:
                node = node.setdefault(ch, {})
            node["end"] = True

    def rebuild(self, words: list[str]):
        self.root = {}
        self._load(BUILTIN_WORDS)
        for w in words:
            w = w.strip()
            if not w:
                continue
            node = self.root
            for ch in w:
                node = node.setdefault(ch, {})
            node["end"] = True

    def hit(self, text: str) -> str | None:
        for i in range(len(text)):
            node = self.root
            for j in range(i, len(text)):
                ch = text[j]
                node = node.get(ch)
                if node is None:
                    break
                if node.get("end"):
                    return text[i:j + 1]
        return None

    def mask(self, text: str) -> str:
        return text


filter_instance = DFAFilter()


def check_sensitive(text: str) -> str | None:
    return filter_instance.hit(text)


def build_from_words(words: list[str]):
    filter_instance.rebuild(words)