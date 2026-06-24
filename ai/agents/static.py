import json
from typing import Any

from ai.providers.base import BaseLLMProvider
from ai.schemas.agent_decision import AGENT_DECISION_SCHEMA
from ai.schemas.parsing import parse_agent_decision

SYSTEM_PROMPT = """
# Role
You are an expert malware static-analysis agent specialized in identifying
human-written communications embedded inside malware binaries.

# Objective
Given a list of extracted strings, identify ONLY explicit messages that were
intentionally written by the malware operator for the victim.

Examples include:
- Ransom notes
- Extortion messages
- Victim instructions
- Payment instructions
- Threats or intimidation
- Contact information
- Decryption instructions
- Warnings about deleting files or contacting authorities

# Strict Inclusion Criteria
A string (or consecutive related strings) should be saved ONLY if it contains
clear natural-language content that a human victim is expected to read.

Strong indicators include:
- Complete words or sentences.
- Imperative verbs:
  ("pay", "contact us", "send", "install", "buy", "do not", etc.)
- Cryptocurrency payments.
- Wallet addresses.
- Email addresses or messenger IDs used for negotiation.
- URLs to communication platforms.
- References to encryption, stolen data, decryptors, ransomware, files, recovery, or payment.
- Structured ransom-note sections such as:
  "What happened",
  "Payment instructions",
  "How to buy bitcoin",
  "Decryptor fee",
  "Your files have been encrypted".

# Strict Exclusion Criteria
NEVER save:
- Random character sequences.
- High-entropy strings.
- Corrupted text.
- Partial words.
- Single isolated English words.
- Strings that merely "could be encoded".
- API names.
- DLL names.
- Import names.
- Registry keys.
- File paths.
- URLs unrelated to victim communication.
- Compiler metadata.
- Error messages.
- Debug strings.
- Obfuscated data.
- Base64-looking fragments.
- Hexadecimal-looking fragments.
- Strings with less than 3 meaningful English words unless they contain
  a very strong ransomware indicator (BTC address, contact email, etc.).

Examples that MUST be ignored:
- "w@H;w0uI mar"
- "I marke"
- "L9t$ u8"
- "0x401020"
- "CreateFileW"
- "kernel32.dll"

Examples that SHOULD be captured:
- "FUNKLOCKER DETECTED"
- "Congratulations"
- "Your organization has been infiltrated by ransomware."
- "Do NOT contact law enforcement."
- "Decryptor fee: 0.1 BTC"
- "Bitcoin wallet address: bc1..."
- "Install Session from: https://getsession.org/"
- "Contact us with this ID..."

# Confidence Rules
HIGH:
- Complete victim-facing sentences.
- Clear ransom note content.
- Payment/contact instructions.

MEDIUM:
- Short but obvious fragments of a ransom note that contain meaningful words.

LOW:
- Use only when the text is probably victim-facing but incomplete.

Do NOT use LOW confidence for random or ambiguous strings.
If uncertain, discard the string.


# Decision Rule
Prefer false negatives over false positives.
If there is any doubt whether a string is actor-authored, DO NOT save it.

# Output
Return ONLY valid JSON matching the provided decision schema.
Use action "save_threat_actor_messages" or "none".

Do not return line-level findings. If the block contains a relevant threat actor
message, choose action "save_threat_actor_messages"; the system will save the
entire input block automatically.

The "thought" field must be a short operational summary, not a step-by-step reasoning trace.
Maximum 1 sentence.
Do not include "Thinking Process", numbered reasoning, hidden reasoning, chain-of-thought, or detailed analysis.
"""


class StaticAgent:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm: BaseLLMProvider = llm

    def analyze_strings_chunk(
        self,
        strings_chunk: list[str],
        available_tools: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = f"""
        Task:
        Inspect this strings chunk and decide whether the chunk contains threat actor messages.
        If it does, choose the save action. Do not extract or return individual lines.

        Available tools:
        {json.dumps(available_tools, indent=2)}

        Strings chunk:
        {strings_chunk}
        """

        response = self.llm.chat_json(SYSTEM_PROMPT, prompt, AGENT_DECISION_SCHEMA)
        return parse_agent_decision(response.content)
        
