from demos.frosty.agent.personality import frosty_personality
from ice_sdk.agents import FlowDesignAssistant


def main():
    # Compose framework with demo personality
    assistant = FlowDesignAssistant(personality=frosty_personality)
    assistant.start_chat("❄️ Welcome to Frosty Flow Designer! ❄️")
