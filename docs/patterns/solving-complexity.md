# Pattern: Solving Complexity with Recursion

This guide explains how to apply the **Fractal Architecture** to solve problems that are too big for a single prompt.

## The Problem: The Complexity Wall

You want to build an agent that can "Write a complete iOS App". If you ask GPT-4 to do this in one go, it will fail. It might give you a generic outline, or a few files, but it will lose context, hallucinate APIs, and hit token limits.

## The Solution: Recursive Decomposition

Instead of one big prompt, we use Loom's **Fractal Pattern**.

### Step 1: Define the Root Agent

The Root Agent is the Project Manager. Its job is NOT to write code, but to plan.

**System Prompt**: "You are a Lead Architect. Break down the app requirements into modules."

### Step 2: The Decomposition

When the Root Agent receives the request, it uses the `FractalOrchestrator` to generate sub-tasks:

1.  "Design the UI System (Views, Themes)"
2.  "Design the Data Layer (CoreData, Models)"
3.  "Implement the Networking Layer (API Client)"

### Step 3: Spawning Specialists

Loom automatically spawns a child agent for each sub-task.

*   **UI Agent**: Sees only the UI requirements. It doesn't care about the API. It has full context window space to focus on SwiftUI.
*   **Data Agent**: Sees only the Data requirements.

### Step 4: Recursive Depth

The **UI Agent** might realize the task is still too big. "Implement all Views" is too much. So it recurses *again*:

*   **Login View Agent**
*   **Home Stream Agent**
*   **Settings Agent**

Now, the "Login View Agent" has a very simple job: "Write `LoginView.swift`". It can do this perfectly.

### Step 5: Synthesis

Once the leaf nodes (the coders) finish, the code bubbles up.
1.  **UI Agent** combines the views into a module.
2.  **Root Agent** combines the modules into a full codebase.

## Summary

By using recursion, we turned an Impossible Task ("Write an App") into 50 Trivial Tasks ("Write a View"). This is the power of Loom.
