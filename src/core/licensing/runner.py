"""Run one license check: probe, extract, classify the outcome. Never raises."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Callable

from . import probes
from .checks import LicenseCheck
from .extract import ExtractError, records_from_output, to_observations
from .models import CheckResult, CheckStatus

Reader = Callable[..., object]


def run_check(check: LicenseCheck, policy: probes.SafetyPolicy, reader: Reader = probes.read) -> CheckResult:
    started_at = datetime.now()
    clock = time.monotonic()

    def result(status: str, licenses=(), error_code: str = "", message: str = "") -> CheckResult:
        return CheckResult(
            check_key=check.key,
            revision=check.revision,
            status=status,
            started_at=started_at,
            duration_ms=int((time.monotonic() - clock) * 1000),
            licenses=tuple(licenses),
            error_code=error_code,
            error_message=message[:200],
        )

    try:
        output = reader(check.probe, policy)
        licenses = to_observations(records_from_output(output, check), check)
    except probes.ProbeRejected as error:
        return result(CheckStatus.REJECTED, error_code=error.error_code, message=str(error))
    except probes.ProbeUnavailable as error:
        return result(CheckStatus.NOT_INSTALLED, error_code="not_installed", message=str(error))
    except probes.ProbeFailed as error:
        return result(CheckStatus.FAILED, error_code=error.error_code, message=str(error))
    except ExtractError as error:
        return result(CheckStatus.FAILED, error_code="parse_error", message=str(error))
    except Exception as error:  # a tool or mapping must never stop the agent
        return result(CheckStatus.FAILED, error_code="internal_error", message=type(error).__name__)
    return result(CheckStatus.OK, licenses)
