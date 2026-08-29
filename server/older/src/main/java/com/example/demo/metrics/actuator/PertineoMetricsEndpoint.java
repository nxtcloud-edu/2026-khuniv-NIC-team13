package com.example.demo.metrics.actuator;

import com.example.demo.metrics.app.MetricsService;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.actuate.endpoint.annotation.Endpoint;
import org.springframework.boot.actuate.endpoint.annotation.ReadOperation;
import org.springframework.boot.actuate.endpoint.annotation.Selector;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 단일 metrics API
 * - GET /actuator/pertineoMetrics            (오늘, Asia/Seoul)
 * - GET /actuator/pertineoMetrics/{date}     (date=YYYY-MM-DD)
 */
@Component
@Endpoint(id = "pertineoMetrics")
@RequiredArgsConstructor
public class PertineoMetricsEndpoint {

    private final MetricsService metricsService;

    @ReadOperation
    public Map<String, Object> metrics() {
        return metrics(LocalDate.now(MetricsService.DEFAULT_ZONE));
    }

    @ReadOperation
    public Map<String, Object> metrics(@Selector String date) {
        try {
            return metrics(LocalDate.parse(date));
        } catch (DateTimeParseException e) {
            // actuator endpoint는 일단 0으로 반환(클라이언트에서 date 포맷을 바로 잡도록)
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("date", date);
            body.put("dailyVisitors", 0);
            body.put("visitorsTotal", metricsService.getVisitorsTotal());
            body.put("analysisTotal", metricsService.getAnalysisTotal());
            body.put("error", "InvalidDateFormat");
            body.put("message", "date must be YYYY-MM-DD");
            return body;
        }
    }

    private Map<String, Object> metrics(LocalDate day) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("date", day.toString());
        body.put("dailyVisitors", metricsService.getDailyVisitors(day));
        body.put("visitorsTotal", metricsService.getVisitorsTotal());
        body.put("analysisTotal", metricsService.getAnalysisTotal());
        return body;
    }
}

