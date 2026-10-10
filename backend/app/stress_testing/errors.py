class StressTestingError(Exception):
    code = "stress_testing_error"


class StressScenarioNotFoundError(StressTestingError):
    code = "scenario_not_found"


class StressPortfolioNotFoundError(StressTestingError):
    code = "portfolio_not_found"


class StressSignalNotFoundError(StressTestingError):
    code = "signal_not_found"


class StressRunNotFoundError(StressTestingError):
    code = "run_not_found"


class StressIneligibleSignalError(StressTestingError):
    code = "signal_ineligible"

    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__(", ".join(reasons))


class StressValidationError(StressTestingError):
    code = "stress_validation_error"
