# loom-agent v0.0.8 Release Guide

This guide walks through publishing loom-agent v0.0.8 to PyPI.

---

## ✅ Pre-Release Checklist

All preparation tasks have been completed:

- [x] Version updated to 0.0.8 in `pyproject.toml`
- [x] README.md updated with v0.0.8 features
- [x] CHANGELOG.md created with complete v0.0.8 notes
- [x] Quick start guide created (`docs/QUICKSTART_v0_0_8.md`)
- [x] API reference updated (`docs/API_REFERENCE_v0_0_8.md`)
- [x] Package built successfully:
  - `loom_agent-0.0.8-py3-none-any.whl` (243 KB)
  - `loom_agent-0.0.8.tar.gz` (191 KB)
- [x] New components verified in package:
  - `execution_frame.py`
  - `event_journal.py`
  - `state_reconstructor.py`
  - `lifecycle_hooks.py`
  - `context_debugger.py`

---

## 📦 Built Artifacts

The following packages are ready in `dist/`:

```
dist/loom_agent-0.0.8-py3-none-any.whl    (243 KB)
dist/loom_agent-0.0.8.tar.gz              (191 KB)
```

---

## 🚀 Publishing to PyPI

### Option 1: Direct Publish with Poetry

```bash
# Configure PyPI token (if not already configured)
poetry config pypi-token.pypi <your-pypi-token>

# Publish to PyPI
poetry publish
```

### Option 2: Publish with Twine

```bash
# Install twine if not already installed
pip install twine

# Upload to PyPI
twine upload dist/loom_agent-0.0.8*
```

### Option 3: Test on TestPyPI First (Recommended)

```bash
# Configure TestPyPI token
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi <your-testpypi-token>

# Publish to TestPyPI
poetry publish -r testpypi

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ loom-agent==0.0.8

# If everything works, publish to PyPI
poetry config pypi-token.pypi <your-pypi-token>
poetry publish
```

---

## 🔍 Post-Release Verification

After publishing, verify the release:

### 1. Check PyPI Page

Visit: https://pypi.org/project/loom-agent/

Verify:
- Version shows as 0.0.8
- README renders correctly
- Package description updated
- Links work correctly

### 2. Test Installation

```bash
# Create fresh virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from PyPI
pip install loom-agent==0.0.8

# Test import
python -c "from loom import agent; print('✅ Import successful')"

# Test new features
python -c "from loom.core import ExecutionFrame, EventJournal, ContextDebugger; print('✅ New components available')"
python -c "from loom.core.lifecycle_hooks import HITLHook, LoggingHook, MetricsHook; print('✅ Hooks available')"
```

### 3. Test Basic Functionality

```bash
# Create test script
cat > test_v0_0_8.py << 'EOF'
import asyncio
from loom import agent
from pathlib import Path
from loom.core.lifecycle_hooks import LoggingHook, MetricsHook

async def test():
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        tools=[],
        enable_persistence=True,
        journal_path=Path("./test_logs"),
        hooks=[LoggingHook(verbose=True), MetricsHook()]
    )

    result = await my_agent.run("Say hello")
    print(f"Result: {result}")
    print("✅ v0.0.8 features working!")

asyncio.run(test())
EOF

# Run test (requires OPENAI_API_KEY)
export OPENAI_API_KEY=your_key_here
python test_v0_0_8.py
```

---

## 📢 Announcement

### GitHub Release

Create a GitHub release at: https://github.com/kongusen/loom-agent/releases/new

**Tag**: `v0.0.8`

**Release Title**: `loom-agent v0.0.8 - Recursive State Machine`

**Description** (use CHANGELOG.md content):

```markdown
# loom-agent v0.0.8 - Recursive State Machine 🎉

Major architectural upgrade from "implicit recursion framework" to production-ready **Recursive State Machine (RSM)**.

## 🌟 Key Features

- 🎬 **Event Sourcing** - Complete execution history with crash recovery
- 🪝 **Lifecycle Hooks** - 9 interception points for elegant control flow
- 🛡️ **HITL Support** - Human-in-the-Loop for dangerous operations
- 🔄 **Crash Recovery** - Resume from any interruption
- 🐛 **Context Debugger** - Transparent context management decisions

## 📊 vs LangGraph

loom-agent v0.0.8 offers unique advantages over LangGraph:
- **Event Sourcing** vs Static Snapshots
- **Strategy Upgrade** - Replay old events with new strategies (unique!)
- **Context Governance** - Full transparency and debugging
- **Hook-based Control** - No explicit graph edges needed

## 📦 Installation

```bash
pip install loom-agent==0.0.8
```

## 📚 Documentation

- [Quick Start Guide](docs/QUICKSTART_v0_0_8.md)
- [API Reference](docs/API_REFERENCE_v0_0_8.md)
- [Architecture Details](docs/ARCHITECTURE_REFACTOR.md)
- [Complete Changelog](CHANGELOG.md)

## 🔗 Links

- **PyPI**: https://pypi.org/project/loom-agent/0.0.8/
- **Docs**: https://github.com/kongusen/loom-agent#readme
- **Examples**: [Integration Example](examples/integration_example.py)

**Full Changelog**: https://github.com/kongusen/loom-agent/blob/main/CHANGELOG.md
```

### Social Media / Community

**Twitter/X**:
```
🚀 loom-agent v0.0.8 is here!

New: Recursive State Machine architecture with:
🎬 Event Sourcing
🪝 Lifecycle Hooks (9 points)
🛡️ HITL Support
🔄 Crash Recovery
🐛 Context Debugger

Unique vs LangGraph: Strategy upgrade during replay!

pip install loom-agent==0.0.8

#AI #LLM #Agents #Python
```

**Reddit (r/LocalLLaMA, r/MachineLearning)**:
```
loom-agent v0.0.8 Released - Recursive State Machine for AI Agents

Major architectural upgrade focused on production reliability:
- Event sourcing for crash recovery
- Lifecycle hooks for elegant control flow
- Human-in-the-Loop (HITL) support
- Context debugging and transparency

Key differentiator vs LangGraph: Can replay old events with new strategies (unique capability!)

PyPI: https://pypi.org/project/loom-agent/0.0.8/
GitHub: https://github.com/kongusen/loom-agent

Would love feedback from the community!
```

---

## 🏷️ Git Tag

Create and push git tag:

```bash
# Create tag
git tag -a v0.0.8 -m "Release v0.0.8 - Recursive State Machine"

# Push tag
git push origin v0.0.8

# Or push all tags
git push origin --tags
```

---

## 📝 Update Documentation

### Update README.md Links

Ensure all links in README.md point to the correct version:

```bash
# Check links
grep -n "v0.0" README.md

# Update any hardcoded version links
```

### Update docs/QUICKSTART.md

If there's a generic quickstart (not v0_0_8 specific), update it to reference the new version:

```markdown
For v0.0.8 features, see [Quick Start v0.0.8](QUICKSTART_v0_0_8.md)
```

---

## 🐛 Post-Release Monitoring

Monitor for issues in the first 24-48 hours:

### 1. GitHub Issues

Watch: https://github.com/kongusen/loom-agent/issues

### 2. PyPI Download Stats

Check: https://pypistats.org/packages/loom-agent

### 3. Common Issues to Watch For

- Import errors with new components
- EventJournal file permission issues
- Hook exceptions not being caught
- Crash recovery failures
- Documentation links broken

---

## 🔄 Next Steps

### Short Term (v0.0.9)

- Fix any critical bugs found in v0.0.8
- Improve test coverage (currently 50%)
- Create MockLLMWithTools helper
- Add more HITL examples

### Medium Term (v0.1.0)

- Web UI for debugging (FastAPI + React)
- Enhanced visualizations
- Plugin system
- Performance benchmarks
- Multiple storage backends (Postgres)

---

## 📞 Support

If issues arise during/after release:

1. **Check build logs**: `poetry build --verbose`
2. **Verify package**: `tar -tzf dist/loom_agent-0.0.8.tar.gz`
3. **Test locally**: Install from wheel file
4. **Rollback if needed**: PyPI doesn't allow overwriting, but can yank version

---

## ✅ Release Checklist Summary

- [ ] Verify all tests passing: `pytest`
- [ ] Build package: `poetry build` (DONE)
- [ ] Test installation locally
- [ ] Publish to TestPyPI (optional but recommended)
- [ ] Publish to PyPI: `poetry publish`
- [ ] Create GitHub release with tag v0.0.8
- [ ] Verify PyPI page renders correctly
- [ ] Test fresh installation from PyPI
- [ ] Announce on social media/community
- [ ] Monitor for issues
- [ ] Update project board/roadmap

---

**You're ready to publish loom-agent v0.0.8! 🎉**

Good luck with the release!
