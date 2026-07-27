"""工作流编排：将原子按 CICCS 五步闭环编排。"""

from typing import Any, Callable, List


class WorkflowStep:
    def __init__(self, name: str, fn: Callable, timeout: float = 30):
        self.name = name
        self.fn = fn
        self.timeout = timeout


class Workflow:
    def __init__(self, name: str):
        self.name = name
        self._steps: List[WorkflowStep] = []

    def add(self, step: WorkflowStep):
        self._steps.append(step)
        return self

    def run(self, context: dict = None) -> dict:
        ctx = dict(context or {})
        for step in self._steps:
            try:
                result = step.fn(ctx)
                if result is not None:
                    ctx[step.name] = result
            except Exception as e:
                ctx.setdefault("_errors", []).append(f"{step.name}: {e}")
        return ctx

    def steps(self) -> List[str]:
        return [s.name for s in self._steps]


def build_trigger_workflow(on_forensics: Callable, on_lockdown: Callable,
                           on_score: Callable, on_counterstrike: Callable,
                           on_notify: Callable) -> Workflow:
    """构建标准触发工作流。"""
    wf = Workflow("trigger")
    wf.add(WorkflowStep("forensics", lambda ctx: on_forensics(ctx)))
    wf.add(WorkflowStep("lockdown", lambda ctx: on_lockdown(ctx)))
    wf.add(WorkflowStep("threat_score", lambda ctx: on_score(ctx)))
    wf.add(WorkflowStep("counterstrike", lambda ctx: on_counterstrike(ctx)))
    wf.add(WorkflowStep("notify", lambda ctx: on_notify(ctx)))
    return wf
