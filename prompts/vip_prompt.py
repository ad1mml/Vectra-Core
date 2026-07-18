from prompts.vip_identity import VIP_IDENTITY
from prompts.vip_reasoning import VIP_REASONING
from prompts.vip_technical import VIP_TECHNICAL
from prompts.vip_fundamental import VIP_FUNDAMENTAL
from prompts.vip_execution import VIP_EXECUTION
from prompts.vip_score import VIP_SCORE
from prompts.vip_memory import VIP_MEMORY
from prompts.vip_coach import VIP_COACH
from prompts.vip_rules import VIP_RULES
from prompts.vip_json import VIP_JSON

VIP_PROMPT = f"""
{VIP_IDENTITY}

{VIP_REASONING}

{VIP_TECHNICAL}

{VIP_FUNDAMENTAL}

{VIP_EXECUTION}

{VIP_SCORE}

{VIP_MEMORY}

{VIP_COACH}

{VIP_RULES}

{VIP_JSON}
"""