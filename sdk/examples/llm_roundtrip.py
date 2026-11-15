"""Send a petition to an AI model without its personal data, then put the values back into the answer.

    pip install "katip-mask[model]" anthropic
    ANTHROPIC_MODEL=<model id> python llm_roundtrip.py dilekce.txt
"""
import os
import sys

import anthropic
from katip_mask import LeakError, Masker

masker = Masker("ai", model="mini")
text = open(sys.argv[1], encoding="utf-8").read()
try:
    masked = masker.mask(text)
except LeakError as e:  # a detected value would have stayed readable: nothing is sent
    sys.exit(f"not sent: {e}")

reply = anthropic.Anthropic().messages.create(
    model=os.environ["ANTHROPIC_MODEL"], max_tokens=1500,
    messages=[{"role": "user", "content": "Bu dilekçeyi özetle, placeholder'ları aynen koru:\n\n" + masked.text}],
)
print(masked.restore(reply.content[0].text))  # the mapping never left this machine
