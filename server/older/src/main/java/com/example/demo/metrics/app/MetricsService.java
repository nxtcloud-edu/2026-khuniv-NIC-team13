package com.example.demo.metrics.app;

import com.example.demo.shared.dynamodb.handler.MetricsHandler;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.ZoneId;

@Service
@RequiredArgsConstructor
public class MetricsService {

    public static final ZoneId DEFAULT_ZONE = ZoneId.of("Asia/Seoul");

    private final MetricsHandler metricsHandler;

    /**
     * /send-verify-email 요청 1회 시도(실패 포함)를 기록합니다.
     * - visitorsTotal: 매 요청 +1
     * - dailyVisitors: day+email 기준 최초 1회만 +1
     */
    public void recordSendVerifyEmailAttempt(String email) {
        metricsHandler.incrementVisitorsTotal();
        metricsHandler.recordDailyUniqueVisitor(LocalDate.now(DEFAULT_ZONE), email);
    }

    /**
     * /analysis 요청 1회 시도(실패 포함)를 기록합니다.
     */
    public void recordAnalysisAttempt() {
        metricsHandler.incrementAnalysisTotal();
    }

    public long getVisitorsTotal() {
        return metricsHandler.getVisitorsTotal();
    }

    public long getAnalysisTotal() {
        return metricsHandler.getAnalysisTotal();
    }

    public long getDailyVisitors(LocalDate day) {
        return metricsHandler.getDailyVisitors(day);
    }
}

