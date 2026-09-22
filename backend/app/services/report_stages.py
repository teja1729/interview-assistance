"""Bounded parallel inference with one coordinator owning all quota/checkpoint writes.

Never share a SQLAlchemy Session or the mutable artifacts dict with executor threads. Completed
stages are saved even if a sibling fails. No new calls are launched after the first failure.
"""

import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass

from ..agents.runtime import execute
from .usage import consume


@dataclass
class Stage:
    name: str
    agent: str
    payload: dict
    schema: type
    validator: object = None


class StageRunner:
    def __init__(self, session, workspace, artifacts, save, kwargs):
        self.session, self.workspace, self.artifacts = session, workspace, artifacts
        self.save, self.kwargs = save, kwargs

    def cached(self, stage):
        saved = self.artifacts["steps"].get(stage.name)
        if saved is None:
            return None
        output = stage.schema.model_validate(saved)
        if stage.validator:
            stage.validator(output)
        return output

    def reserve(self, stage):
        self.artifacts["active_stage"] = stage.name
        self.save()
        consume(self.session, self.workspace)

    def infer(self, stage):
        return execute(
            stage.agent, stage.payload, stage.schema, stage=stage.name, validate=stage.validator, **self.kwargs
        )

    def persist(self, stage, output):
        self.artifacts["steps"][stage.name] = output.model_dump()
        self.save()

    def run(self, name, agent, payload, schema, validator=None):
        stage = Stage(name, agent, payload, schema, validator)
        if (saved := self.cached(stage)) is not None:
            return saved
        self.reserve(stage)
        output = self.infer(stage)
        self.persist(stage, output)
        return output

    def parallel(self, stages, concurrency=2):
        outputs, todo = {}, []
        for stage in stages:
            cached = self.cached(stage)
            if cached is None:
                todo.append(stage)
            else:
                outputs[stage.name] = cached
        remaining = iter(todo)
        error = None
        can_save = True
        renewed = time.monotonic()
        pending = {}
        with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="report-topic") as pool:
            while True:
                while not error and len(pending) < concurrency:
                    stage = next(remaining, None)
                    if stage is None:
                        break
                    try:
                        self.reserve(stage)
                        pending[pool.submit(self.infer, stage)] = stage
                    except Exception as exc:  # noqa: BLE001 - drain already-started work before propagating
                        error = exc
                        break
                if not pending:
                    break
                finished, _ = wait(pending, timeout=5, return_when=FIRST_COMPLETED)
                if can_save and time.monotonic() - renewed > 45:
                    try:
                        self.save()
                        renewed = time.monotonic()
                    except Exception as exc:  # noqa: BLE001 - lost lease/database failure prevents writes
                        error, can_save = error or exc, False
                for future in finished:
                    stage = pending.pop(future)
                    try:
                        output = future.result()
                    except Exception as exc:  # noqa: BLE001 - preserve successful sibling checkpoints
                        error = error or exc
                        continue
                    if can_save:
                        try:
                            self.persist(stage, output)
                            outputs[stage.name] = output
                        except Exception as exc:  # noqa: BLE001 - do not publish after losing the lease
                            error, can_save = error or exc, False
        if error:
            raise error
        return outputs
