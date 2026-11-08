import logging

import grpc

from app.grpc import ecos_forecast_pb2, ecos_forecast_pb2_grpc
from app.services.epidemiology import VALID_DISEASES
from app.services.prediction import predict_cases
from app.services.model_registry import get_served_model_name

logger = logging.getLogger(__name__)


def _to_points(rows: list[dict]) -> list[ecos_forecast_pb2.PredictionPoint]:
    out = []
    for p in rows:
        out.append(
            ecos_forecast_pb2.PredictionPoint(
                epi_year=int(p.get("epi_year", 0)),
                epi_week=int(p.get("epi_week", 0)),
                predicted_cases=float(p.get("predicted_cases", 0)),
                outbreak_flag=bool(p.get("outbreak_flag", False)),
            )
        )
    return out


class ForecastServicer(ecos_forecast_pb2_grpc.ForecastServiceServicer):
    def Health(self, request, context):  # noqa: N802
        return ecos_forecast_pb2.HealthResponse(status="ok")

    def WhatIf(self, request, context):  # noqa: N802
        disease = request.disease
        if disease not in VALID_DISEASES:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"disease must be one of {sorted(VALID_DISEASES)}")
            return ecos_forecast_pb2.WhatIfResponse()

        weeks = request.weeks_ahead or 2
        if weeks < 1 or weeks > 4:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("weeks_ahead must be 1..4")
            return ecos_forecast_pb2.WhatIfResponse()

        adjustments = dict(request.adjustments) if request.adjustments else None
        try:
            original = predict_cases(request.municipio_code, disease, weeks_ahead=weeks)
            adjusted = predict_cases(
                request.municipio_code,
                disease,
                weeks_ahead=weeks,
                adjustments=adjustments,
            )
        except Exception as exc:
            logger.warning("gRPC WhatIf failed: %s", exc)
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(str(exc))
            return ecos_forecast_pb2.WhatIfResponse()

        delta = sum(p["predicted_cases"] for p in adjusted) - sum(p["predicted_cases"] for p in original)
        return ecos_forecast_pb2.WhatIfResponse(
            original=_to_points(original),
            adjusted=_to_points(adjusted),
            delta_total=round(delta, 2),
            model_family=get_served_model_name(),
        )
