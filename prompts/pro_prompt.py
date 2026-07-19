from prompts.pro_identity import PRO_IDENTITY
from prompts.pro_technical import PRO_TECHNICAL
from prompts.pro_execution import PRO_EXECUTION
from prompts.pro_score import PRO_SCORE
from prompts.pro_rules import PRO_RULES
from prompts.pro_reasoning import PRO_REASONING
from prompts.pro_json import PRO_JSON
from prompts.pro_coach import PRO_COACH

PRO_PROMPT = f"""
{PRO_IDENTITY}

{PRO_TECHNICAL}

{PRO_EXECUTION}

{PRO_SCORE}

{PRO_RULES}

{PRO_REASONING}

{PRO_COACH}

{PRO_JSON}
"""