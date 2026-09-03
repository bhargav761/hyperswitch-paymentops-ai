RECOVERY_ANALYSIS_PROMPT = """
Analyze the payment failure using the supplied payment state and recovery
knowledge. Return the likely root cause, supporting evidence, confidence,
and safest recovery recommendation. Never bypass policy or approval controls.
""".strip()
