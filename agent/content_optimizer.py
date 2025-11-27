# Already in ai_rewrite_page(); add more prompts here.
def add_schema(content):
    return content + """
<FAQPage>
  <mainEntity>
    <Question><text>What is SabaiFly?</text></Question>
    <Answer>...</Answer>
  </mainEntity>
</FAQPage>
"""
