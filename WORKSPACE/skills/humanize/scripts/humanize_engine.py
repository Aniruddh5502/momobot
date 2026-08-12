import random
import re

class HumanizerEngine:
    """
    Advanced text degradation engine inspired by Sinceerly.
    Moves from simple replacement to structural and lexical humanization.
    """
    
    def __init__(self):
        # High-probability AI markers and their human equivalents
        self.lexicon_map = {
            "In conclusion": "Basically",
            "Furthermore": "Also",
            "Moreover": "Plus",
            "It is important to note that": "Just so you know,",
            "Additionally": "And also",
            "I hope this email finds you well": "Hey,",
            "Please feel free to": "Just",
            "Consequently": "So",
            "Nevertheless": "Still",
            "Utilize": "Use",
            "Essentially": "Basically",
            "Moreover": "And",
            "Therefore": "So",
            "Thus": "So",
            "Indeed": "Yeah",
            "It is evident that": "Clearly",
            "A variety of": "some",
            "In order to": "to",
            "Despite the fact that": "Even though",
            "Due to the fact that": "Because"
        }
        
        self.contractions = {
            "do not": "don't",
            "cannot": "can't",
            "it is": "it's",
            "I am": "I'm",
            "we are": "we're",
            "you are": "you're",
            "they are": "they're",
            "do not": "don't",
            "will not": "won't",
            "should not": "shouldn't",
            "could not": "couldn't",
            "would not": "wouldn't"
        }

        # Keyboard proximity map for realistic typos (QWERTY)
        self.keyboard_proximity = {
            'a': 'sqw', 'b': 'vghn', 'c': 'xdfv', 'd': 'sfr', 'e': 'rdw',
            'f': 'dgtr', 'g': 'fhjt', 'h': 'gjkn', 'i': 'uok', 'j': 'hkl',
            'k': 'jl', 'l': 'ko', 'm': 'nk', 'n': 'bhj', 'o': 'ikp',
            'p': 'ol', 'q': 'wa', 'r': 'edft', 's': 'awdx', 't': 'rfgy',
            'u': 'yjh', 'v': 'cfgb', 'w': 'qeas', 'x': 'zs', 'y': 'tuh',
            'z': 'asx'
        }

    def _break_sentences(self, text):
        """Breaks overly formal, long AI sentences into shorter, punchier ones."""
        # Look for typical AI transition markers followed by long clauses
        patterns = [
            (r", however, ", ". However, "),
            (r", therefore, ", ". So, "),
            (r", moreover, ", ". Also, "),
            (r"; ", ". ")
        ]
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _inject_typos(self, text, probability):
        """Injects realistic, keyboard-proximity based typos."""
        words = text.split()
        processed_words = []
        
        for word in words:
            if len(word) > 3 and random.random() < probability:
                idx = random.randint(1, len(word) - 2)
                chars = list(word.lower())
                char = chars[idx]
                
                if char in self.keyboard_proximity:
                    # Swap with a nearby key
                    chars[idx] = random.choice(self.keyboard_proximity[char])
                else:
                    # Random drop if no proximity available
                    if random.random() < 0.5:
                        chars.pop(idx)
                
                # Preserve original casing if possible
                word = "".join(chars)
                if word[0].isupper(): #’s a very basic check
                    word = word.capitalize()
            processed_words.append(word)
        
        return " ".join(processed_words)

    def humanize(self, text, profile="casual"):
        """
        Pipeline for humanization:
        Structure -> Lexicon -> Contractions -> Noise
        """
        try:
            # 1. Structural shift (sentence breaking)
            text = self._break_sentences(text)

            # 2. Lexical Replacement
            for formal, casual in self.lexicon_map.items():
                text = re.sub(rf'\b{formal}\b', casual, text, flags=re.IGNORECASE)

            # 3. Contraction Enforcement
            for formal, casual in self.contractions.items():
                text = re.sub(rf'\b{formal}\b', casual, text, flags=re.IGNORECASE)

            # 4. Profile-based Noise
            profiles = {
                "casual": 0.03, # Reduced for better readability
                "distracted": 0.10,
                "non-native": 0.06
            }
            noise_level = profiles.get(profile, 0.03)
            text = self._inject_typos(text, noise_level)

            return text
        except Exception as e:
            print(f"Humanizer Error: {e}")
            return text

if __name__ == "__main__":
    import sys
    engine = HumanizerEngine()
    
    # Handle CLI input if provided
    if len(sys.argv) > 1:
        input_text = " ".join(sys.argv[1:])
        profile = "casual"
        if "distracted" in sys.argv: profile = "distracted"
        if "non-native" in sys.argv: profile = "non-native"
        print(engine.humanize(input_text, profile))
    else:
        sample = "In conclusion, it is important to note that I am unable to attend the meeting. Furthermore, I do not have the documents."
        print(f"Original: {sample}")
        print(f"Casual: {engine.humanize(sample, 'casual')}")
        print(f"Distracted: {engine.humanize(sample, 'distracted')}")
