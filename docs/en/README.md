# Loom Agent Documentation

> Cognitive Dynamics based Event-Driven Agent Framework

## 🚀 Quick Start

**Get started in 5 minutes:**

```python
from loom.weave import create_agent, run

agent = create_agent("Assistant", role="General Assistant")
result = run(agent, "Hello, please introduce yourself")
```

👉 [Full Quick Start Guide](getting-started/quickstart.md)

---

## 📚 Documentation Navigation

This documentation is organized based on the [Diátaxis](https://diataxis.fr/) framework, divided into four parts:

### 📖 [Tutorials](tutorials/)
**Learning-oriented** - Learn loom-agent step by step

- [Create Your First Agent](tutorials/your-first-agent.md)
- [Add Skills to Agent](tutorials/adding-skills.md)
- [Build Agent Teams](tutorials/building-teams.md)
- [Use YAML Configuration](tutorials/yaml-configuration.md)

### 🛠️ [How-to Guides](guides/)
**Problem-oriented** - Solve specific problems

- [Agents](guides/agents/) - Create and configure Agents
- [Skills](guides/skills/) - Develop custom skills
- [Configuration](guides/configuration/) - Configuration and deployment
- [Deployment](guides/deployment/) - Production deployment

### 💡 [Concepts](concepts/)
**Understanding-oriented** - Deep dive into core concepts

- [Architecture Design](concepts/architecture.md)
- [Cognitive Dynamics](concepts/cognitive-dynamics.md)
- [Design Philosophy](concepts/design-philosophy.md)

### 📚 [Reference](reference/)
**Information-oriented** - Complete API documentation

- [loom.weave API](reference/api/weave.md)
- [loom.stdlib API](reference/api/stdlib.md)
- [Configuration Reference](reference/api/config.md)
- [Example Code](reference/examples/)

---

## 🎯 Choose based on your needs

**I am a beginner and want to start quickly:**
→ Start with [Quick Start](getting-started/quickstart.md)

**I want to learn systematically:**
→ Read [Tutorials](tutorials/) in order

**I encountered a specific problem:**
→ Check [How-to Guides](guides/)

**I want to understand the principles deeply:**
→ Read [Concepts](concepts/)

**I need to check the API:**
→ Consult [Reference](reference/)
