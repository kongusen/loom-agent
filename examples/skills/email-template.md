---
name: email-template
description: Generate email templates with named parameters
whenToUse: email, template, message
allowedTools: []
userInvocable: true
---

# Email Template Generator

Generate a professional email template.

## Template

**To:** ${recipient}
**From:** ${sender}
**Subject:** ${subject}

Dear ${recipient},

${message}

Best regards,
${sender}

---

**Skill Directory:** ${CLAUDE_SKILL_DIR}
**Session ID:** ${CLAUDE_SESSION_ID}
