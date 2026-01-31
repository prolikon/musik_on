from typing import List, Set

import regex


def _detect_scripts(char: str) -> Set[str]:
    scripts = set()
    if regex.match(r"\p{Latin}", char):
        scripts.add("Latin")
    if (
        regex.match(r"\p{Han}", char)
        or regex.match(r"\p{Hiragana}", char)
        or regex.match(r"\p{Katakana}", char)
    ):
        scripts.add("Japanese")  # This will match Chinese too (shoutout to China)
    if regex.match(r"\p{Hangul}", char):
        scripts.add("Hangul")
    if regex.match(r"\p{Common}", char):
        scripts.add("Common")
    return scripts if scripts else {"Other"}


def extract_script_segments(text: str) -> List[str]:
    if not text:
        return []

    results = []

    # Step 1: Extract bracketed content
    bracket_pattern = regex.compile(
        r"(?:\(([^)]*)\)|\[([^\]]*)\]|\{([^}]*)\}|<([^>]*)>)"
    )

    bracket_contents = []

    def replace_bracket(match):
        content = next(g for g in match.groups() if g is not None)
        bracket_contents.append(content.strip())
        return " "  # Preserve spacing

    cleaned_text = bracket_pattern.sub(replace_bracket, text)
    results.extend(bracket_contents)

    # Step 2: Script-based grouping
    # words = cleaned_text.split()
    words = text.split()
    if not words:
        return results

    segments = []
    current_segment = []
    current_scripts = set()

    for word in words:
        # Determine scripts used in this word
        word_scripts = set()
        for char in word:
            word_scripts.update(_detect_scripts(char))

        # Remove Common (punctuation) for matching logic
        effective_scripts = word_scripts - {"Common", "Other"}
        if not effective_scripts:
            effective_scripts = {"Other"}

        if not current_segment:
            # Start first segment
            current_segment = [word]
            current_scripts = effective_scripts.copy()
        else:
            # Check if this word shares any script with current segment
            if effective_scripts & current_scripts:
                # Continue segment and expand allowed scripts (handles mixed script propagation)
                current_segment.append(word)
                current_scripts |= effective_scripts
            else:
                # Close current segment and start new one
                segments.append(" ".join(current_segment))
                current_segment = [word]
                current_scripts = effective_scripts.copy()

    if current_segment:
        segments.append(" ".join(current_segment))

    results.extend(segments)
    return results
