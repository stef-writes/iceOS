class PersonalityManager:
    def load(self, style: str) -> dict:
        # Separate tone/behavior from core logic
        return {
            "frosty": {
                "greeting": "❄️ Let's chill-aborate on your flow!",
                "error_response": "Brrr...that input froze me. Try again?",
            },
            "professional": {
                "greeting": "Welcome to the iceOS Flow Designer.",
                "error_response": "Invalid input detected. Please rephrase.",
            },
        }


# Convenience constant so other demos can import directly
personality_manager = PersonalityManager()
frosty_personality = personality_manager.load("frosty")["frosty"]
